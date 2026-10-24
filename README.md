# Readiness и liveness в Kubernetes

Этот пример XNova показывает, почему временная неготовность приложения не должна автоматически приводить к перезапуску контейнера. Один HTTP-сервер отвечает на `/ready` и `/live`; файл на `emptyDir` позволяет переключать каждый сигнал отдельно.

## Требования и локальная проверка

Нужны Docker, kind, совместимый с кластером `kubectl` и Python 3.12. Команды ниже рассчитаны на терминал macOS или Linux; в Windows используйте PowerShell и подставьте имя Pod вручную. Dockerfile закрепляет Python 3.12.12 по digest. Версии FastAPI, Uvicorn и их зависимостей закреплены в `requirements.txt`; зависимости локальных проверок находятся в `requirements-dev.txt`.

```bash
git clone https://github.com/xnova-tech/kubernetes-probes-example.git
cd kubernetes-probes-example
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python probe_smoke.py
.venv/bin/python -m pytest -q
docker build -t xnova-probes:local .
```

В Windows создайте окружение командой `py -3.12 -m venv .venv` и замените `.venv/bin/python` на `.venv\Scripts\python.exe`. Smoke через FastAPI `TestClient` проверяет последовательность ответов `(live, ready)`: `(200, 200)` → `(200, 503)` → `(200, 200)`, затем отдельный отказ liveness `(503, 200)` и восстановление `(200, 200)`. Регрессионные тесты дополнительно проверяют тело, тип ответа и переменные окружения. Эти проверки не проверяют Kubernetes.

## Запуск кластера

Создайте отдельный локальный кластер и загрузите в него только что собранный образ. Перед применением файлов убедитесь, что выбран именно `kind-probes-lab`.

```bash
kind create cluster --name probes-lab
kind load docker-image xnova-probes:local --name probes-lab
kubectl config current-context
kubectl apply --dry-run=server -f service.yaml
kubectl apply --dry-run=server -f bad.yaml
kubectl apply --dry-run=server -f good.yaml
```

Контекст должен быть `kind-probes-lab`. Обе конфигурации Deployment используют одну реплику и один Service. `bad.yaml` направляет обе probes на `/ready`; `good.yaml` меняет только liveness на `/live`.

## Воспроизведение ошибки

```bash
kubectl apply -f service.yaml
kubectl apply -f bad.yaml
kubectl rollout status deployment/probe-demo
kubectl get pods -l app=probe-demo -o json
kubectl get endpointslices -l kubernetes.io/service-name=probe-demo -o json
kubectl get events --sort-by=.lastTimestamp
```

Запишите `metadata.uid`, Pod `Ready` и `status.containerStatuses[].restartCount` до отказа. Возьмите имя Pod из `kubectl get pods -l app=probe-demo`. Создайте флаг и повторите три команды наблюдения через 30 секунд:

```bash
kubectl exec POD_NAME -- touch /state/unready
kubectl get pods -l app=probe-demo -o json
kubectl get endpointslices -l kubernetes.io/service-name=probe-demo -o json
kubectl get events --sort-by=.lastTimestamp
```

`/ready` возвращает `503`; поскольку ошибочная liveness проверяет тот же путь, kubelet должен перезапустить контейнер после заданного порога. Сравнивайте `restartCount` **того же Pod UID** с начальным значением. Файл остаётся на `emptyDir` в прежнем Pod, поэтому рестарт контейнера не снимает неготовность. EndpointSlice оценивайте по `endpoints[].conditions`, а не по наличию адреса.

## Исправление и контроль

Применение `good.yaml` создаёт новый Pod, поэтому снимите новую базовую точку. Не сравнивайте его абсолютный `restartCount` со старым Pod.

```bash
kubectl apply -f good.yaml
kubectl rollout status deployment/probe-demo
kubectl get pods -l app=probe-demo -o json
kubectl exec POD_NAME -- touch /state/unready
kubectl get pods -l app=probe-demo -o json
kubectl get endpointslices -l kubernetes.io/service-name=probe-demo -o json
kubectl exec POD_NAME -- rm /state/unready
kubectl get pods -l app=probe-demo -o json
```

Подставьте имя **нового** Pod. Во время неготовности `/live` остаётся `200`, `Ready` становится `false`, а `restartCount` за сопоставимое окно не должен расти из-за этого флага. После удаления флага дождитесь `Ready=true` и `ready=true` у endpoint.

Отдельный отрицательный контроль проверяет, что исправленная liveness всё ещё обнаруживает отказ своего маршрута:

```bash
kubectl exec POD_NAME -- touch /state/unlive
kubectl get pods -l app=probe-demo -o json
kubectl get events --sort-by=.lastTimestamp
kubectl exec POD_NAME -- rm /state/unlive
```

Дождитесь превышения `livenessProbe.failureThreshold`; `restartCount` этого Pod должен увеличиться. Удалите флаг, чтобы восстановить `/live`. Если exec попал в окно рестарта, повторите удаление после запуска контейнера. Сверьте `metadata.uid`: рост счётчика в том же UID означает рестарт контейнера, другой UID означает замену Pod.

Этот стенд с одной репликой показывает реакцию probes и EndpointSlice, но не доказывает доступность многорепличного сервиса или отсутствие потерь уже открытых соединений. Файл-флаг не моделирует настоящую базу данных; FastAPI здесь обслуживает только два лабораторных сигнала.

## Очистка

```bash
kind delete cluster --name probes-lab
```

Исходники доступны по лицензии Apache-2.0 в `LICENSE`.
