/* 
   Código ESP32 Simplificado para Lector de Registro USB (RFID a Serial)
   Este firmware es ideal para el ESP32 conectado directamente a la laptop.
   Solo lee tarjetas RFID y las envía formateadas por puerto USB Serial a la GUI.
   Sin Wi-Fi, sin HTTP, sin esperas por red. ¡Velocidad instantánea!
*/

#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "esp_log.h"

/* Pines de Conexión (RC522) */
#define PIN_NUM_MISO 19
#define PIN_NUM_MOSI 23
#define PIN_NUM_CLK  18
#define PIN_NUM_CS   5
#define PIN_NUM_RST  22

#define SPI_HOST     SPI2_HOST

static spi_device_handle_t spi;

/* Funciones de bajo nivel para RC522 */
void rc522_write(uint8_t reg, uint8_t value) {
    spi_transaction_t t = {0};
    uint8_t data[2] = {(reg << 1) & 0x7E, value};
    t.length = 16;
    t.tx_buffer = data;
    spi_device_transmit(spi, &t);
}

uint8_t rc522_read(uint8_t reg) {
    spi_transaction_t t = {0};
    uint8_t tx[2] = {((reg << 1) & 0x7E) | 0x80, 0x00};
    uint8_t rx[2];
    t.length = 16;
    t.tx_buffer = tx;
    t.rx_buffer = rx;
    spi_device_transmit(spi, &t);
    return rx[1];
}

void rc522_set_bitmask(uint8_t reg, uint8_t mask) { rc522_write(reg, rc522_read(reg) | mask); }
void rc522_clear_bitmask(uint8_t reg, uint8_t mask) { rc522_write(reg, rc522_read(reg) & ~mask); }

void rc522_reset() {
    gpio_set_level(PIN_NUM_RST, 0);
    vTaskDelay(pdMS_TO_TICKS(50));
    gpio_set_level(PIN_NUM_RST, 1);
    vTaskDelay(pdMS_TO_TICKS(50));
}

void rc522_init() {
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

    int i = 2000;
    while (i-- && !(rc522_read(0x04) & 0x30));
    rc522_clear_bitmask(0x0D, 0x80);

    if (i <= 0) return false;
    if (rc522_read(0x06) & 0x1B) return false;
    if (rc522_read(0x0A) != 5) return false;

    for (int j = 0; j < 5; j++)
        uid[j] = rc522_read(0x09);

    return true;
}

void rfid_task(void *arg) {
    uint8_t uid[5];
    while (1) {
        if (rc522_request() && rc522_anticoll(uid)) {
            char uid_str[11] = "";
            for (int i = 0; i < 4; i++) {
                sprintf(uid_str + i * 2, "%02X", uid[i]);
            }
            // Envía por serial en el formato JSON esperado por el Panel de Administración
            printf("{\"uid\":\"%s\"}\n", uid_str);
            fflush(stdout); // Asegura envío inmediato
            
            vTaskDelay(pdMS_TO_TICKS(1500)); // Espera para evitar lecturas duplicadas
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

void app_main(void) {
    // Configurar pines SPI
    spi_bus_config_t buscfg = {
        .miso_io_num = PIN_NUM_MISO,
        .mosi_io_num = PIN_NUM_MOSI,
        .sclk_io_num = PIN_NUM_CLK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1
    };
    spi_bus_initialize(SPI_HOST, &buscfg, SPI_DMA_CH_AUTO);

    spi_device_interface_config_t devcfg = {
        .clock_speed_hz = 1000000,
        .mode = 0,
        .spics_io_num = PIN_NUM_CS,
        .queue_size = 1
    };
    spi_bus_add_device(SPI_HOST, &devcfg, &spi);

    gpio_set_direction(PIN_NUM_RST, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_NUM_RST, 1);

    rc522_init();
    
    // Leer el registro de versión del RC522 (0x37) para verificar si hay conexión SPI
    uint8_t version = rc522_read(0x37);
    printf(">> INITIALIZATION DEBUG: RC522 Firmware Version: 0x%02X\n", version);
    if (version == 0x00 || version == 0xFF) {
        printf(">> ERROR: RC522 NO DETECTADO. ¡Revisa los cables MISO, MOSI, SCK, CS, RST y la corriente (3.3V)!\n");
    } else {
        printf(">> ÉXITO: RC522 detectado y listo para leer.\n");
    }
    
    // Lanzar solo la tarea de lectura serial
    xTaskCreate(rfid_task, "rfid_task", 4096, NULL, 5, NULL);
}
