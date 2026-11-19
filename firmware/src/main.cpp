#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include "config.h"

constexpr uint8_t LED_RED = 47;
constexpr uint8_t LED_GREEN = 36;
constexpr uint8_t LED_WHITE = 37;
constexpr unsigned long REPORT_INTERVAL_MS = 30000;
constexpr unsigned long CONNECT_TIMEOUT_MS = 15000;

enum class DeviceState { Starting, Connecting, Online, ReportingError };

DeviceState state = DeviceState::Starting;
unsigned long lastReport = 0;
unsigned long connectStarted = 0;

void setLeds(bool red, bool green, bool white) {
  digitalWrite(LED_RED, red ? HIGH : LOW);
  digitalWrite(LED_GREEN, green ? HIGH : LOW);
  digitalWrite(LED_WHITE, white ? HIGH : LOW);
}

void setState(DeviceState next) {
  state = next;
  switch (state) {
    case DeviceState::Starting: setLeds(false, false, true); break;
    case DeviceState::Connecting: setLeds(false, false, true); break;
    case DeviceState::Online: setLeds(false, true, false); break;
    case DeviceState::ReportingError: setLeds(true, false, false); break;
  }
}

String telemetryUrl() {
  return String(USB_SENTINEL_API_BASE) + "/api/sessions/" +
         USB_SENTINEL_SESSION_ID + "/telemetry";
}

bool postTelemetry() {
  if (WiFi.status() != WL_CONNECTED) return false;
  HTTPClient http;
  http.setConnectTimeout(3000);
  http.setTimeout(5000);
  if (!http.begin(telemetryUrl())) return false;
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", USB_SENTINEL_API_TOKEN);
  String payload = "{\"deviceId\":\"" USB_SENTINEL_DEVICE_ID "\",\"metrics\":{";
  payload += "\"uptimeMs\":" + String(millis());
  payload += ",\"wifiRssi\":" + String(WiFi.RSSI());
  payload += ",\"freeHeapBytes\":" + String(ESP.getFreeHeap());
  payload += ",\"firmware\":\"1.0.0\"}}";
  const int code = http.POST(payload);
  http.end();
  Serial.printf("[telemetry] HTTP %d\n", code);
  return code >= 200 && code < 300;
}

void beginConnection() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(USB_SENTINEL_WIFI_SSID, USB_SENTINEL_WIFI_PASSWORD);
  connectStarted = millis();
  setState(DeviceState::Connecting);
  Serial.println("[wifi] connecting");
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_RED, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_WHITE, OUTPUT);
  setState(DeviceState::Starting);
  beginConnection();
}

void loop() {
  const unsigned long now = millis();
  if (WiFi.status() != WL_CONNECTED) {
    if (state != DeviceState::Connecting || now - connectStarted > CONNECT_TIMEOUT_MS) {
      WiFi.disconnect();
      beginConnection();
    }
    delay(25);
    return;
  }
  if (state == DeviceState::Connecting) {
    Serial.print("[wifi] connected: ");
    Serial.println(WiFi.localIP());
    setState(DeviceState::Online);
  }
  if (now - lastReport >= REPORT_INTERVAL_MS || lastReport == 0) {
    lastReport = now;
    setState(postTelemetry() ? DeviceState::Online : DeviceState::ReportingError);
  }
  delay(25);
}
