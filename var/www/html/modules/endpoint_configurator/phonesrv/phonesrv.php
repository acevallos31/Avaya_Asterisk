<?php
function writeLog($message) {
    $logFile = "/var/log/phonesrv_debug.log";
    $message = "[DEBUG] " . $message;
    file_put_contents($logFile, date("[Y-m-d H:i:s] ") . $message . PHP_EOL, FILE_APPEND | LOCK_EX);
    if (!file_exists($logFile)) chmod($logFile, 0666);
}
