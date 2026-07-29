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
#include "driver/i2c.h"
#include "esp_vfs_fat.h"
#include "sdmmc_cmd.h"
#include "driver/sdspi_host.h"

/* I2C y Hardware Config */
#define I2C_EEPROM_SDA_IO           32
#define I2C_EEPROM_SCL_IO           33
#define I2C_EEPROM_NUM              0

#define I2C_RTC_SDA_IO              13
#define I2C_RTC_SCL_IO              14
#define I2C_RTC_NUM                 1

#define I2C_MASTER_FREQ_HZ          100000
#define I2C_MASTER_TX_BUF_DISABLE   0
#define I2C_MASTER_RX_BUF_DISABLE   0

#define DS1307_ADDR                 0x68
#define EEPROM_ADDR                 0x50
#define EEPROM_MAGIC_BYTE           0xAB

#define PIN_NUM_SD_CS               15
#define PIN_NUM_SD_MISO             25
#define PIN_NUM_SD_MOSI             26
#define PIN_NUM_SD_CLK              27

static sdmmc_card_t *sd_card = NULL;

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

/* ── Funciones Hardware (I2C, RTC, EEPROM, SD) ────────────────── */
static esp_err_t i2c_master_init(void) {
    // I2C 0 para EEPROM
    i2c_config_t conf_eeprom = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = I2C_EEPROM_SDA_IO,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_io_num = I2C_EEPROM_SCL_IO,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = I2C_MASTER_FREQ_HZ,
    };
    esp_err_t err = i2c_param_config(I2C_EEPROM_NUM, &conf_eeprom);
    if (err != ESP_OK) return err;
    err = i2c_driver_install(I2C_EEPROM_NUM, conf_eeprom.mode, I2C_MASTER_RX_BUF_DISABLE, I2C_MASTER_TX_BUF_DISABLE, 0);
    if (err != ESP_OK) return err;

    // I2C 1 para RTC
    i2c_config_t conf_rtc = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = I2C_RTC_SDA_IO,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_io_num = I2C_RTC_SCL_IO,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = I2C_MASTER_FREQ_HZ,
    };
    err = i2c_param_config(I2C_RTC_NUM, &conf_rtc);
    if (err != ESP_OK) return err;
    return i2c_driver_install(I2C_RTC_NUM, conf_rtc.mode, I2C_MASTER_RX_BUF_DISABLE, I2C_MASTER_TX_BUF_DISABLE, 0);
}

static uint8_t bcd2dec(uint8_t val) { return ((val / 16 * 10) + (val % 16)); }
static uint8_t dec2bcd(uint8_t val) { return ((val / 10 * 16) + (val % 10)); }

void rtc_get_time(struct tm *timeinfo) {
    uint8_t data[7];
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (DS1307_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, 0x00, true);
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (DS1307_ADDR << 1) | I2C_MASTER_READ, true);
    i2c_master_read(cmd, data, 6, I2C_MASTER_ACK);
    i2c_master_read_byte(cmd, data + 6, I2C_MASTER_NACK);
    i2c_master_stop(cmd);
    i2c_master_cmd_begin(I2C_RTC_NUM, cmd, 1000 / portTICK_PERIOD_MS);
    i2c_cmd_link_delete(cmd);

    timeinfo->tm_sec = bcd2dec(data[0] & 0x7F);
    timeinfo->tm_min = bcd2dec(data[1]);
    timeinfo->tm_hour = bcd2dec(data[2] & 0x3F);
    timeinfo->tm_wday = bcd2dec(data[3]) - 1;
    timeinfo->tm_mday = bcd2dec(data[4]);
    timeinfo->tm_mon  = bcd2dec(data[5]) - 1;
    timeinfo->tm_year = bcd2dec(data[6]) + 100;
}

void rtc_set_time(struct tm *timeinfo) {
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (DS1307_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, 0x00, true);
    i2c_master_write_byte(cmd, dec2bcd(timeinfo->tm_sec), true);
    i2c_master_write_byte(cmd, dec2bcd(timeinfo->tm_min), true);
    i2c_master_write_byte(cmd, dec2bcd(timeinfo->tm_hour), true);
    i2c_master_write_byte(cmd, dec2bcd(timeinfo->tm_wday + 1), true);
    i2c_master_write_byte(cmd, dec2bcd(timeinfo->tm_mday), true);
    i2c_master_write_byte(cmd, dec2bcd(timeinfo->tm_mon + 1), true);
    i2c_master_write_byte(cmd, dec2bcd(timeinfo->tm_year - 100), true);
    i2c_master_stop(cmd);
    i2c_master_cmd_begin(I2C_RTC_NUM, cmd, 1000 / portTICK_PERIOD_MS);
    i2c_cmd_link_delete(cmd);
}

void sync_system_from_rtc() {
    struct tm timeinfo = {0};
    rtc_get_time(&timeinfo);
    if (timeinfo.tm_year > 100) {
        time_t t = mktime(&timeinfo);
        struct timeval now = { .tv_sec = t, .tv_usec = 0 };
        settimeofday(&now, NULL);
        ESP_LOGI("RTC", "Sistema sincronizado con RTC: %02d/%02d/%04d %02d:%02d:%02d", 
            timeinfo.tm_mday, timeinfo.tm_mon + 1, timeinfo.tm_year + 1900, timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);
    }
}

void time_sync_notification_cb(struct timeval *tv) {
    time_t now = 0;
    struct tm timeinfo = {0};
    time(&now);
    localtime_r(&now, &timeinfo);
    rtc_set_time(&timeinfo);
    ESP_LOGI("RTC", "Hora guardada en RTC desde internet.");
}

esp_err_t eeprom_write(uint16_t mem_address, uint8_t *data, size_t size) {
    for (size_t i = 0; i < size; i++) {
        i2c_cmd_handle_t cmd = i2c_cmd_link_create();
        i2c_master_start(cmd);
        i2c_master_write_byte(cmd, (EEPROM_ADDR << 1) | I2C_MASTER_WRITE, true);
        i2c_master_write_byte(cmd, (mem_address + i) >> 8, true);
        i2c_master_write_byte(cmd, (mem_address + i) & 0xFF, true);
        i2c_master_write_byte(cmd, data[i], true);
        i2c_master_stop(cmd);
        esp_err_t ret = i2c_master_cmd_begin(I2C_EEPROM_NUM, cmd, 1000 / portTICK_PERIOD_MS);
        i2c_cmd_link_delete(cmd);
        if (ret != ESP_OK) return ret;
        vTaskDelay(pdMS_TO_TICKS(10));
    }
    return ESP_OK;
}

esp_err_t eeprom_read(uint16_t mem_address, uint8_t *data, size_t size) {
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (EEPROM_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, mem_address >> 8, true);
    i2c_master_write_byte(cmd, mem_address & 0xFF, true);
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (EEPROM_ADDR << 1) | I2C_MASTER_READ, true);
    if (size > 1) i2c_master_read(cmd, data, size - 1, I2C_MASTER_ACK);
    i2c_master_read_byte(cmd, data + size - 1, I2C_MASTER_NACK);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(I2C_EEPROM_NUM, cmd, 1000 / portTICK_PERIOD_MS);
    i2c_cmd_link_delete(cmd);
    return ret;
}

void save_tarjetas_to_eeprom() {
    uint8_t meta[2] = {EEPROM_MAGIC_BYTE, total_tarjetas};
    eeprom_write(0x0000, meta, 2);
    for (int i = 0; i < total_tarjetas; i++) {
        eeprom_write(0x0002 + (i * 4), tarjetas[i], 4);
    }
    ESP_LOGI("EEPROM", "Guardadas %d tarjetas", total_tarjetas);
}

void load_tarjetas_from_eeprom() {
    uint8_t meta[2];
    if (eeprom_read(0x0000, meta, 2) == ESP_OK && meta[0] == EEPROM_MAGIC_BYTE) {
        total_tarjetas = meta[1] > MAX_TARJETAS ? MAX_TARJETAS : meta[1];
        for (int i = 0; i < total_tarjetas; i++) {
            eeprom_read(0x0002 + (i * 4), tarjetas[i], 4);
        }
        ESP_LOGI("EEPROM", "Cargadas %d tarjetas", total_tarjetas);
    } else {
        ESP_LOGW("EEPROM", "Memoria vacia o error al leer");
    }
}

void init_sd_card() {
    esp_vfs_fat_sdmmc_mount_config_t mount_config = {
        .format_if_mount_failed = true,
        .max_files = 5,
        .allocation_unit_size = 16 * 1024
    };
    sdmmc_host_t host = SDSPI_HOST_DEFAULT();
    host.slot = SPI3_HOST;
    sdspi_device_config_t slot_config = SDSPI_DEVICE_CONFIG_DEFAULT();
    slot_config.gpio_cs = PIN_NUM_SD_CS;
    slot_config.host_id = SPI3_HOST;
    esp_err_t ret = esp_vfs_fat_sdspi_mount("/sdcard", &host, &slot_config, &mount_config, &sd_card);
    if (ret != ESP_OK) {
        ESP_LOGE("SD", "Fallo al inicializar la tarjeta SD (%s)", esp_err_to_name(ret));
    } else {
        ESP_LOGI("SD", "Tarjeta SD montada exitosamente");
    }
}

void log_to_sd(const char *uid_str, bool acces_granted) {
    if (sd_card == NULL) return;
    FILE *f = fopen("/sdcard/historial.txt", "a");
    if (f != NULL) {
        time_t now; time(&now);
        struct tm timeinfo; localtime_r(&now, &timeinfo);
        char time_str[64];
        strftime(time_str, sizeof(time_str), "%Y-%m-%d %H:%M:%S", &timeinfo);
        fprintf(f, "[%s] UID: %s | Acceso: %s\n", time_str, uid_str, acces_granted ? "PERMITIDO" : "DENEGADO");
        fclose(f);
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
                log_to_sd(uid_str, true);
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
                log_to_sd(uid_str, false);
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
                    save_tarjetas_to_eeprom();
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
    esp_sntp_set_time_sync_notification_cb(time_sync_notification_cb);
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

    // Inicializar un segundo bus SPI independiente para la tarjeta SD
    spi_bus_config_t buscfg_sd = {.miso_io_num = PIN_NUM_SD_MISO, .mosi_io_num = PIN_NUM_SD_MOSI, .sclk_io_num = PIN_NUM_SD_CLK, .quadwp_io_num = -1, .quadhd_io_num = -1};
    spi_bus_initialize(SPI3_HOST, &buscfg_sd, SPI_DMA_CH_AUTO);

    gpio_set_direction(PIN_NUM_RST, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_NUM_RST, 1);
    
    gpio_set_direction(PIN_LED_VERDE, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_LED_VERDE, 0);

    gpio_set_direction(PIN_LED_ROJO, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_LED_ROJO, 0);

    gpio_reset_pin(PIN_LED_AZUL);
    gpio_set_direction(PIN_LED_AZUL, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_LED_AZUL, 1);

    // Inicializar I2C (EEPROM y RTC)
    i2c_master_init();
    sync_system_from_rtc();
    load_tarjetas_from_eeprom();

    // Inicializar Micro SD
    init_sd_card();

    rc522_init();
    
    // Leer el registro de versión del RC522 (0x37) para verificar si hay conexión SPI
    uint8_t version = rc522_read(0x37);
    ESP_LOGI("SPI", "INITIALIZATION DEBUG: RC522 Firmware Version: 0x%02X", version);
    if (version == 0x00 || version == 0xFF) {
        ESP_LOGE("SPI", "ERROR: RC522 NO DETECTADO. ¡Revisa los cables MISO, MOSI, SCK, CS, RST y la corriente (3.3V)!");
    } else {
        ESP_LOGI("SPI", "ÉXITO: RC522 detectado y listo para leer.");
    }

    xTaskCreate(rfid_task, "rfid_task", 4096, NULL, 5, NULL);
    xTaskCreate(http_sync_task, "http_sync_task", 6144, NULL, 5, NULL);
}