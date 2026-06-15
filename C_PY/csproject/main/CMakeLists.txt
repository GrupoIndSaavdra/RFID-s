idf_component_register(SRCS "csproject.c"
                    INCLUDE_DIRS "."
                    PRIV_REQUIRES esp_http_client json esp_driver_spi esp_driver_gpio esp_wifi esp_netif nvs_flash esp_event)
