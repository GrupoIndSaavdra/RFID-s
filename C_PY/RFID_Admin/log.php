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
        $stmt2 = $conn->prepare("INSERT INTO registros_acceso (uid, area, fecha, tipo) VALUES (?, ?, FROM_UNIXTIME(?), ?)");
        $stmt2->bind_param("ssis", $uid, $area_nombre, $ts, $tipo_puerta);
    } else {
        $stmt2 = $conn->prepare("INSERT INTO registros_acceso (uid, area, tipo) VALUES (?, ?, ?)");
        $stmt2->bind_param("sss", $uid, $area_nombre, $tipo_puerta);
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
