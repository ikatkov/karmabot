# Copyright (c) 2019 Target Brands, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from functools import wraps
import os
import time

from opentelemetry import metrics


def _configure_meter_provider():
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return

    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource

    service_name = os.environ.get("OTEL_SERVICE_NAME", "karmabot")
    exporter = OTLPMetricExporter()
    reader = PeriodicExportingMetricReader(exporter)
    provider = MeterProvider(
        metric_readers=[reader],
        resource=Resource.create({"service.name": service_name}),
    )
    metrics.set_meter_provider(provider)


_configure_meter_provider()
_meter = metrics.get_meter("karmabot")
_counters = {}
_histograms = {}


class timeit(object):
    def __init__(self, measurement, tags=None, field="time_elapsed"):
        self.measurement = measurement
        self.tags = tags
        self.field = field

    def __call__(self, f):

        @wraps(f)
        def timed(*args, **kwargs):
            ts = time.time()
            result = f(*args, **kwargs)
            te = time.time()
            value = int((te - ts) * 1000)
            log_metrics(self.measurement, self.tags, self.field, value)

            return result
        return timed


def _attributes(tags):
    return tags or {}


def _counter(name):
    if name not in _counters:
        _counters[name] = _meter.create_counter(name, unit="1")
    return _counters[name]


def _histogram(name, unit):
    if name not in _histograms:
        _histograms[name] = _meter.create_histogram(name, unit=unit)
    return _histograms[name]


def log_metrics(measurement, tags, field, value):
    if field == "count" and measurement != "threads":
        _counter(measurement).add(value, attributes=_attributes(tags))
        return

    metric_name = measurement if field == "time_elapsed" else f"{measurement}.{field}"
    unit = "ms" if field == "time_elapsed" else "1"
    _histogram(metric_name, unit).record(value, attributes=_attributes(tags))
