<?php
// C:\xampp\htdocs\log.php
// Endpoint para que el ESP32 registre un acceso autorizado

header('Content-Type: application/json');

$host = "127.0.0.1";
$user = "root";
$pass = "";
$db = "rfid_db";

$conn = new mysqli($host, $user, $pass, $db);

if ($conn->connect_error) {
    die(json_encode(["error" => "Error de conexion: " . $conn->connect_error]));
}

$uid = isset($_GET['uid']) ? $_GET['uid'] : '';
$mac = isset($_GET['mac']) ? $_GET['mac'] : '';

if ($uid !== '' && $mac !== '') {
    // Buscar qué área es basándonos en la MAC
    $stmt = $conn->prepare("SELECT area_id, tipo FROM puertas WHERE mac_address = ?");
    $stmt->bind_param("s", $mac);
    $stmt->execute();
    $res = $stmt->get_result();
    
    $area_nombre = "Desconocida";
    $tipo_puerta = "Entrada";
    
    if ($row = $res->fetch_assoc()) {
        $area_id = $row['area_id'];
        if (isset($row['tipo'])) {
            $tipo_puerta = $row['tipo'];
        }
        $nombres_areas = [
            "1" => "Baños",
            "2" => "Programación-Software",
            "3" => "Calidad",
            "4" => "Almacén",
            "5" => "RH",
            "6" => "Mantenimiento",
            "7" => "Comedor",
            "8" => "Gerencia",
            "9" => "Producción",
            "10" => "Sala de Juntas"
        ];
        if (isset($nombres_areas[$area_id])) {
            $area_nombre = $nombres_areas[$area_id];
        }
    }
    $stmt->close();

    $ts = isset($_GET['ts']) ? $_GET['ts'] : '';
    
    if (is_numeric($ts) && $ts > 1000000000) {
        // Verificar que el timestamp no provenga de un glitch en el RTC (ej. año 2035/2036)
        // Si el timestamp está más de 1 hora en el futuro, usar la hora actual del servidor.
        if (intval($ts) > time() + 3600) {
            $timestamp_val = "NOW()";
        } else {
            $timestamp_val = "FROM_UNIXTIME(" . intval($ts) . ")";
        }
    } else {
        $timestamp_val = "NOW()";
    }

    if ($tipo_puerta === "Entrada") {
        $stmt_check = $conn->prepare("SELECT id FROM registros_acceso WHERE uid = ? AND tipo = 'Entrada' AND fecha >= DATE_SUB($timestamp_val, INTERVAL 2 MINUTE) AND fecha_salida IS NULL ORDER BY id DESC LIMIT 1");
        $stmt_check->bind_param("s", $uid);
        $stmt_check->execute();
        $res_check = $stmt_check->get_result();
        if ($res_check->fetch_assoc()) {
            echo json_encode(["status" => "ok", "msg" => "Ignored, passed < 2 mins ago"]);
            $stmt_check->close();
            $conn->close();
            exit();
        }
        $stmt_check->close();

        $stmt2 = $conn->prepare("INSERT INTO registros_acceso (uid, area, fecha, tipo) VALUES (?, ?, $timestamp_val, 'Entrada')");
        $stmt2->bind_param("ss", $uid, $area_nombre);
    } else {
        $stmt_check = $conn->prepare("SELECT id FROM registros_acceso WHERE uid = ? AND DATE(fecha) = DATE($timestamp_val) AND fecha_salida IS NULL ORDER BY id DESC LIMIT 1");
        $stmt_check->bind_param("s", $uid);
        $stmt_check->execute();
        $res_check = $stmt_check->get_result();
        if ($row = $res_check->fetch_assoc()) {
            $log_id = $row['id'];
            $stmt2 = $conn->prepare("UPDATE registros_acceso SET fecha_salida = $timestamp_val WHERE id = ?");
            $stmt2->bind_param("i", $log_id);
        } else {
            $stmt2 = $conn->prepare("INSERT INTO registros_acceso (uid, area, fecha, tipo, fecha_salida) VALUES (?, ?, NULL, 'Salida', $timestamp_val)");
            $stmt2->bind_param("ss", $uid, $area_nombre);
        }
        $stmt_check->close();
    }
    
    if ($stmt2->execute()) {
        echo json_encode(["status" => "ok"]);
    } else {
        echo json_encode(["error" => "Error al insertar"]);
    }
    $stmt2->close();
} else {
    echo json_encode(["error" => "Faltan parametros"]);
}

$conn->close();
?>
