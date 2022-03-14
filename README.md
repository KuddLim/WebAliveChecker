# WebAliveChecker
웹 서버의 정상동작여부를 판별하기 위해 접속시도 후, status 코드로 서버의 상태를 판별하는 센서. EW11, HF2211 의 동작 체크를 위해 사용할 수 있다.

## 설치방법
HACS 에서 본 github url 등록

## 설정방법
configuration.yaml 에 다음 항목 추가

```
sensor:
  - platform: web_alive_checker
    sensors:
      my_sensor_name:
        name: "name to display"
        url: "url to check"
        expected_status: 401
        interval: 300
```
