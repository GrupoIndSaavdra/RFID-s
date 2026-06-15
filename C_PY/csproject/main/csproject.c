/* Código ESP32 para manejo de tarjetas RFID y comunicación con Python */
/* Librerías */
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "nvs_flash.h"
#include "esp_netif.h"
#include "lwip/inet.h"
#include "esp_http_client.h"
#include "cJSON.h"
#include <time.h>
#include <sys/time.h>
#include "esp_sntp.h"

/* Configuracion Wi-Fi */
#define WIFI_SSID "Alejandro"
#define WIFI_PASS "123456789"

/* Variable global para almacenar la MAC Address */
char mac_address_str[18] = {0};

/* Pines */
#define PIN_NUM_MISO 19
#define PIN_NUM_MOSI 23
#define PIN_NUM_CLK 18
#define PIN_NUM_CS 5
#define PIN_NUM_RST 22
#define PIN_LED_VERDE 2 /* LED Verde */
#define PIN_LED_ROJO 4 /* LED Rojo para tarjetas denegadas */
#define PIN_LED_AZUL 21 /* LED Azul */
/* SPI y Config */
#define SPI_HOST SPI2_HOST
#define MAX_TARJETAS 50

static spi_device_handle_t spi; /*Manejador del dispositivo SPI para el RC522*/

/* Modos de operación */
typedef enum
{
    MODO_NORMAL,
    MODO_ADD,
    MODO_DEL
} modo_t;
static modo_t modo = MODO_NORMAL;

/* Almacenamiento de tarjetas */
static uint8_t tarjetas[MAX_TARJETAS][5];
static int total_tarjetas = 0;

/* Funciones SPI para RC522 */
void rc522_write(uint8_t reg, uint8_t value)
{
    spi_transaction_t t = {0};
    uint8_t data[2] = {(reg << 1) & 0x7E, value};
    t.length = 16;
    t.tx_buffer = data;
    spi_device_transmit(spi, &t);
}

uint8_t rc522_read(uint8_t reg)
{
    spi_transaction_t t = {0};
    uint8_t tx[2] = {((reg << 1) & 0x7E) | 0x80, 0x00}; /*El bit de lectura se establece en 1*/
    uint8_t rx[2];
    t.length = 16;
    t.tx_buffer = tx;
    t.rx_buffer = rx;
    spi_device_transmit(spi, &t);
    return rx[1];
}

void rc522_set_bitmask(uint8_t reg, uint8_t mask) { rc522_write(reg, rc522_read(reg) | mask); }
void rc522_clear_bitmask(uint8_t reg, uint8_t mask) { rc522_write(reg, rc522_read(reg) & ~mask); }
/*Reset del RC522*/
void rc522_reset()
{
    gpio_set_level(PIN_NUM_RST, 0);
    vTaskDelay(pdMS_TO_TICKS(50));
    gpio_set_level(PIN_NUM_RST, 1);
    vTaskDelay(pdMS_TO_TICKS(50));
}
/*Inicialización del RC522*/
void rc522_init()
{
    rc522_reset();
    rc522_write(0x01, 0x0F);
    vTaskDelay(pdMS_TO_TICKS(50));
    rc522_write(0x2A, 0x8D);
    rc522_write(0x2B, 0x3E);
    rc522_write(0x2D, 30);
    rc522_write(0x2C, 0);
    rc522_write(0x15, 0x40);
    rc522_write(0x11, 0x3D);
    rc522_set_bitmask(0x14, 0x03);
}

/*Funciones para manejar tarjetas*/
bool rc522_request() {
    rc522_write(0x01, 0x00);
    rc522_write(0x02, 0x77 | 0x80);
    rc522_write(0x04, 0x7F);
    rc522_set_bitmask(0x0A, 0x80);
    rc522_write(0x0D, 0x07);
    rc522_write(0x09, 0x26);
    rc522_write(0x01, 0x0C);
    rc522_set_bitmask(0x0D, 0x80);

    int i = 2000;
    while (i-- && !(rc522_read(0x04) & 0x30));
    rc522_clear_bitmask(0x0D, 0x80);

    if (i <= 0) return false;
    if (rc522_read(0x06) & 0x1B) return false;
    if (rc522_read(0x0A) != 2) return false;
    return true;
}
/*Función para obtener el UID de una tarjeta*/
bool rc522_anticoll(uint8_t *uid) { 
    rc522_write(0x01, 0x00);
    rc522_write(0x02, 0x77 | 0x80);
    rc522_write(0x04, 0x7F);
    rc522_set_bitmask(0x0A, 0x80);
    rc522_write(0x0D, 0x00);
    rc522_write(0x09, 0x93);
    rc522_write(0x09, 0x20);
    rc522_write(0x01, 0x0C);
    rc522_set_bitmask(0x0D, 0x80);

    /* Esperar a que se complete la lectura */
    int i = 2000;
    while (i-- && !(rc522_read(0x04) & 0x30));
    rc522_clear_bitmask(0x0D, 0x80);
    /**/
    if (i <= 0) return false;
    if (rc522_read(0x06) & 0x1B) return false;
    if (rc522_read(0x0A) != 5) return false;

    for (int j = 0; j < 5; j++)
        uid[j] = rc522_read(0x09);

    return true;
}
bool tarjeta_existe(uint8_t *uid)
{
    for (int i = 0; i < total_tarjetas; i++) /*Recorrer la lista de tarjetas*/
        if (memcmp(tarjetas[i], uid, 4) == 0)
            return true;
    return false;
}
void agregar_tarjeta(uint8_t *uid) /*Función para agregar una nueva tarjeta*/
{
    if (total_tarjetas >= MAX_TARJETAS || tarjeta_existe(uid))
        return;
    memcpy(tarjetas[total_tarjetas], uid, 4);
    total_tarjetas++;
}
void eliminar_tarjeta(uint8_t *uid) /*Función para eliminar una tarjeta existente*/
{
    for (int i = 0; i < total_tarjetas; i++)
    {
        if (memcmp(tarjetas[i], uid, 4) == 0) /*Si se encuentra la tarjeta*/
        {
            for (int j = i; j < total_tarjetas - 1; j++)
                memcpy(tarjetas[j], tarjetas[j + 1], 4);
            total_tarjetas--;
            return;
        }
    }
}

/* Conversión de hexadecimal a bytes */
void hexStringToBytes(char *hex, uint8_t *bytes)
{
    for (int i = 0; i < 4; i++) {
        unsigned int val;
        sscanf(hex + 2 * i, "%2x", &val);
        bytes[i] = (uint8_t)val;
    }
}

/* ── Sistema de Logs Offline en Memoria Caché ────────────────── */
#define MAX_OFFLINE_LOGS 100

typedef struct {
    char uid[11];
    time_t timestamp;
} offline_log_t;

static offline_log_t offline_logs[MAX_OFFLINE_LOGS];
static int offline_log_head = 0;
static int offline_log_tail = 0;
static int offline_log_count = 0;

void enqueue_offline_log(const char *uid_str, time_t ts)
{
    if (offline_log_count >= MAX_OFFLINE_LOGS) {
        // Cola llena, descartar el más antiguo (desplazar cabeza)
        offline_log_head = (offline_log_head + 1) % MAX_OFFLINE_LOGS;
        offline_log_count--;
        ESP_LOGW("LOG", "Cola offline llena, descartando log antiguo");
    }
    strncpy(offline_logs[offline_log_tail].uid, uid_str, 10);
    offline_logs[offline_log_tail].uid[10] = '\0';
    offline_logs[offline_log_tail].timestamp = ts;
    
    offline_log_tail = (offline_log_tail + 1) % MAX_OFFLINE_LOGS;
    offline_log_count++;
    ESP_LOGI("LOG", "Log guardado en caché offline: %s en ts %ld. Total acumulados: %d", uid_str, (long)ts, offline_log_count);
}

/* Enviar log via Wi-Fi */
bool send_log_wifi(const char *uid_str, time_t ts)
{
    char url[250];
    snprintf(url, sizeof(url), "http://192.168.137.1/log.php?uid=%s&mac=%s&ts=%ld", uid_str, mac_address_str, (long)ts);
    esp_http_client_config_t config = {
        .url = url,
        .timeout_ms = 2000,
    };
    esp_http_client_handle_t client = esp_http_client_init(&config);
    esp_err_t err = esp_http_client_perform(client);
    bool success = false;
    if (err == ESP_OK) {
        int status_code = esp_http_client_get_status_code(client);
        if (status_code == 200) {
            ESP_LOGI("LOG", "Log enviado por Wi-Fi correctamente: %s", uid_str);
            success = true;
        } else {
            ESP_LOGE("LOG", "Servidor respondió con código: %d", status_code);
        }
    } else {
        ESP_LOGE("LOG", "Error enviando log %s: %s", uid_str, esp_err_to_name(err));
    }
    esp_http_client_cleanup(client);
    return success;
}

void flush_offline_logs()
{
    if (offline_log_count == 0) return;
    
    ESP_LOGI("LOG", "¡Conexión recuperada! Vaciando %d logs guardados en caché...", offline_log_count);
    while (offline_log_count > 0) {
        char *uid_str = offline_logs[offline_log_head].uid;
        time_t ts = offline_logs[offline_log_head].timestamp;
        
        if (send_log_wifi(uid_str, ts)) {
            offline_log_head = (offline_log_head + 1) % MAX_OFFLINE_LOGS;
            offline_log_count--;
            vTaskDelay(pdMS_TO_TICKS(100)); // Pausa breve entre envíos para no saturar
        } else {
            ESP_LOGW("LOG", "Fallo al enviar log offline, posponiendo resto del vaciado");
            break;
        }
    }
    if (offline_log_count == 0) {
        ESP_LOGI("LOG", "Todos los logs offline fueron enviados con éxito");
    }
}

/* Tarea RFID */
void rfid_task(void *arg)
{
    uint8_t uid[5];
    while (1)
    {
        if (rc522_request() && rc522_anticoll(uid)) /*Si se detecta una tarjeta*/
        {
            char uid_str[11] = ""; /*Array para almacenar el UID en formato hexadecimal*/
            for (int i = 0; i < 4; i++)
                sprintf(uid_str + i * 2, "%02X", uid[i]); /*Convertir cada byte del UID a su representación hexadecimal y concatenarla en uid_str*/
            
            /* (Opcional) Aún puedes enviarlo por serial si alguien lo está escuchando */
            printf("{\"uid\":\"%s\"}\n", uid_str);
            
            time_t current_time = time(NULL);
            
            /* Encender LED verde si la tarjeta está en memoria */
            if (tarjeta_existe(uid)) {
                gpio_set_level(PIN_LED_VERDE, 1);
                gpio_set_level(PIN_LED_AZUL, 0);
                if (!send_log_wifi(uid_str, current_time)) {
                    enqueue_offline_log(uid_str, current_time);
                }
                vTaskDelay(pdMS_TO_TICKS(1000));
                gpio_set_level(PIN_LED_VERDE, 0);
                vTaskDelay(pdMS_TO_TICKS(4000));
                gpio_set_level(PIN_LED_AZUL, 1);
            } else {
                gpio_set_level(PIN_LED_ROJO, 1);
                if (!send_log_wifi(uid_str, current_time)) {
                    enqueue_offline_log(uid_str, current_time);
                }
                vTaskDelay(pdMS_TO_TICKS(1000)); 
                gpio_set_level(PIN_LED_ROJO, 0);
            }
        }
        vTaskDelay(pdMS_TO_TICKS(200)); /*Pequeña espera para reducir carga de la CPU*/
    }
}

/* Tarea HTTP Sync */
void http_sync_task(void *arg)
{
    while (1) {
        char url[200];
        snprintf(url, sizeof(url), "http://192.168.137.1/api.php?mac=%s", mac_address_str);
        
        esp_http_client_config_t config = {
            .url = url,
            .timeout_ms = 5000,
        };
        esp_http_client_handle_t client = esp_http_client_init(&config);
        
        esp_err_t err = esp_http_client_open(client, 0);
        if (err == ESP_OK) {
            flush_offline_logs();
            esp_http_client_fetch_headers(client);
            char buffer[1024] = {0};
            int read_len = esp_http_client_read_response(client, buffer, sizeof(buffer) - 1);
            if (read_len >= 0) {
                buffer[read_len] = '\0';
                ESP_LOGI("HTTP", "Recibido JSON");
                cJSON *json = cJSON_Parse(buffer);
                if (json != NULL) {
                    int count = cJSON_GetArraySize(json);
                    total_tarjetas = 0; /* Limpiar memoria para la actualizacion */
                    for (int i = 0; i < count && i < MAX_TARJETAS; i++) {
                        cJSON *item = cJSON_GetArrayItem(json, i);
                        if (cJSON_IsString(item) && item->valuestring != NULL) {
                            if (strlen(item->valuestring) >= 8) {
                                uint8_t uid_bytes[4];
                                hexStringToBytes(item->valuestring, uid_bytes);
                                ESP_LOGI("HTTP", "Guardando tarjeta: %02X%02X%02X%02X", uid_bytes[0], uid_bytes[1], uid_bytes[2], uid_bytes[3]);
                                agregar_tarjeta(uid_bytes);
                            }
                        }
                    }
                    cJSON_Delete(json);
                    ESP_LOGI("HTTP", "Sincronizacion completada. Tarjetas en memoria: %d", total_tarjetas);
                } else {
                    ESP_LOGE("HTTP", "Error parseando JSON. Posiblemente desconectado de BD.");
                }
            } else {
                ESP_LOGE("HTTP", "Error leyendo respuesta del servidor");
            }
        } else {
            ESP_LOGE("HTTP", "Error conectando al servidor XAMPP (192.168.137.1)");
        }
        esp_http_client_cleanup(client);
        
        vTaskDelay(pdMS_TO_TICKS(10000)); /* Consultar cada 10 segundos */
    }
}

/* Wi-Fi Handler y Setup */
void initialize_sntp(void)
{
    ESP_LOGI("NTP", "Inicializando SNTP");
    esp_sntp_setoperatingmode(SNTP_OPMODE_POLL);
    esp_sntp_setservername(0, "pool.ntp.org");
    esp_sntp_init();
    
    // Configurar Zona Horaria a México Central (CST/CDT)
    setenv("TZ", "CST6CDT,M4.1.0,M10.5.0", 1);
    tzset();
}

static void wifi_event_handler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data) {
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        ESP_LOGI("WIFI", "Conexion perdida, reintentando...");
        esp_wifi_connect();
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
        ESP_LOGI("WIFI", "¡Conectado a Internet! IP Asignada: " IPSTR, IP2STR(&event->ip_info.ip));
        // Inicializar sincronización de tiempo (NTP) cuando nos conectamos
        initialize_sntp();
    }
}

void wifi_init_sta(void) {
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    
    esp_netif_t *sta_netif = esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    // Obtener la dirección MAC
    uint8_t mac[6];
    esp_wifi_get_mac(WIFI_IF_STA, mac);
    snprintf(mac_address_str, sizeof(mac_address_str), "%02X:%02X:%02X:%02X:%02X:%02X", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    ESP_LOGI("WIFI", "MAC Address de este ESP32: %s", mac_address_str);

    esp_event_handler_instance_t instance_any_id;
    esp_event_handler_instance_t instance_got_ip;
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL, &instance_any_id));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL, &instance_got_ip));

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = WIFI_SSID,
            .password = WIFI_PASS,
            .threshold.authmode = WIFI_AUTH_WPA2_PSK,
        },
    };
    
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());
    
    // Desactivar ahorro de energia para evitar perdida de paquetes/ping
    ESP_ERROR_CHECK(esp_wifi_set_ps(WIFI_PS_NONE));
    
    ESP_LOGI("WIFI", "wifi_init_sta completado. Conectando a %s", WIFI_SSID);
}

/*Main*/
void app_main(void)
{
    // Inicializar NVS (requerido por el Wi-Fi)
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
      ESP_ERROR_CHECK(nvs_flash_erase());
      ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // Inicializar Wi-Fi
    wifi_init_sta();

    spi_bus_config_t buscfg = {.miso_io_num = PIN_NUM_MISO, .mosi_io_num = PIN_NUM_MOSI, .sclk_io_num = PIN_NUM_CLK, .quadwp_io_num = -1, .quadhd_io_num = -1};
    spi_bus_initialize(SPI_HOST, &buscfg, SPI_DMA_CH_AUTO); 

    spi_device_interface_config_t devcfg = {.clock_speed_hz = 1000000, .mode = 0, .spics_io_num = PIN_NUM_CS, .queue_size = 1};
    spi_bus_add_device(SPI_HOST, &devcfg, &spi);

    gpio_set_direction(PIN_NUM_RST, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_NUM_RST, 1);
    
    gpio_set_direction(PIN_LED_VERDE, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_LED_VERDE, 0);

    gpio_set_direction(PIN_LED_ROJO, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_LED_ROJO, 0);

    gpio_reset_pin(PIN_LED_AZUL);
    gpio_set_direction(PIN_LED_AZUL, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_LED_AZUL, 1);

    rc522_init();
    xTaskCreate(rfid_task, "rfid_task", 4096, NULL, 5, NULL);
    xTaskCreate(http_sync_task, "http_sync_task", 6144, NULL, 5, NULL);
}