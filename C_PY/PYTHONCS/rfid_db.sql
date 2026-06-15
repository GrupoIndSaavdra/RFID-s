-- ============================================================
-- SQL para crear la base de datos RFID en XAMPP / phpMyAdmin
-- Ejecuta este script en: http://localhost/phpmyadmin
-- ============================================================

-- 1. Crear la base de datos
CREATE DATABASE IF NOT EXISTS rfid_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE rfid_db;

-- 2. Crear la tabla de tarjetas
CREATE TABLE IF NOT EXISTS tarjetas (
    id              INT AUTO_INCREMENT PRIMARY KEY             COMMENT 'ID autoincrementable',
    uid             VARCHAR(8)   NOT NULL UNIQUE               COMMENT 'UID de la tarjeta RFID (8 chars hex, mayusculas)',
    nombre          VARCHAR(100) NOT NULL                      COMMENT 'Nombre del propietario',
    areas           VARCHAR(50)  NOT NULL                      COMMENT 'Numeros de areas con acceso, separados por coma. Ej: 1,3,5',
    fecha_registro  DATETIME     DEFAULT CURRENT_TIMESTAMP     COMMENT 'Fecha y hora de primer registro',
    fecha_modificado DATETIME    DEFAULT CURRENT_TIMESTAMP
                                 ON UPDATE CURRENT_TIMESTAMP   COMMENT 'Ultima modificacion',
    activa          TINYINT(1)   NOT NULL DEFAULT 1            COMMENT '1=tarjeta activa, 0=desactivada/eliminada',

    INDEX idx_uid    (uid),
    INDEX idx_activa (activa)

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Tarjetas RFID registradas con propietario y areas de acceso';


-- ============================================================
-- REFERENCIA DE AREAS (valores validos para la columna "areas")
-- ============================================================
-- 1  Banos
-- 2  Programacion
-- 3  Calidad
-- 4  Almacen
-- 5  RH
-- 6  Mantenimiento
--
-- Ejemplo de fila:
--   uid='A1B2C3D4', nombre='Juan Perez', areas='1,3,5'
--   → acceso a Banos, Calidad y RH
-- ============================================================


-- 3. (Opcional) Insertar tarjeta de prueba
-- INSERT INTO tarjetas (uid, nombre, areas) VALUES ('A1B2C3D4', 'Usuario Prueba', '1,2');


-- 4. Verificar que la tabla fue creada correctamente
DESCRIBE tarjetas;
SELECT * FROM tarjetas;

-- ============================================================
-- 5. Crear la tabla de puertas ESP32 (Mapeo MAC -> Area)
-- ============================================================
CREATE TABLE IF NOT EXISTS puertas (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    mac_address VARCHAR(20) NOT NULL UNIQUE COMMENT 'MAC del ESP32 (ej. A1:B2:C3:D4:E5:F6)',
    nombre      VARCHAR(100) NOT NULL       COMMENT 'Nombre descriptivo de la puerta',
    area_id     VARCHAR(10) NOT NULL        COMMENT 'ID del area a la que pertenece'
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Registro de ESP32s instalados en las puertas y sus areas asignadas';
