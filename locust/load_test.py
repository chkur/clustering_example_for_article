import argparse
import csv
import logging
import os
from html import escape
from io import StringIO
from itertools import chain
from random import uniform
from time import time
from typing import Any, Dict, List, Optional

import gevent
from flask import (
    Flask,
    Response,
    jsonify,
    make_response,
    request,
    send_file,
)
from flask_basicauth import BasicAuth
from flask_cors import CORS

import locust.stats as stats_module
from locust import FastHttpUser, between, events, tag, task
from locust.env import Environment
from locust.exception import AuthCredentialsError
from locust.html import get_html_report
from locust.log import greenlet_exception_logger, setup_logging
from locust.runners import STATE_MISSING, STATE_RUNNING, MasterRunner
from locust.stats import (
    StatsCSV,
    StatsCSVFileWriter,
    StatsErrorDict,
    sort_stats,
    stats_history,
    stats_printer,
)
from locust.user.inspectuser import get_ratio
from locust.util.cache import memoize
from locust.util.rounding import proper_round
from locust.util.timespan import parse_timespan
from locust.web import DEFAULT_CACHE_TIME, WebUI

min_lat = 41.64449686770894
max_lat = 42.02266026807753
min_lon = -87.91372610600482
max_lon = -87.52447794994927

env = None

setup_logging("INFO", None)
logger = logging.getLogger(__name__)
greenlet_exception_handler = greenlet_exception_logger(logger)
map_result = {}
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
LOCUST_INDEX_HTML = "index.html"


def render_template(file, **kwargs):
    from jinja2 import Environment, FileSystemLoader

    templates_path = os.path.join(BASE_PATH, "templates")
    env = Environment(
        loader=FileSystemLoader(templates_path), extensions=["jinja2.ext.do"]
    )
    template = env.get_template(file)
    return template.render(**kwargs)


@events.request.add_listener
def stats_request_handler(
    request_type,
    name,
    response_time,
    response_length,
    response,
    context,
    exception,
    start_time,
    url,
    **kwargs,
):
    if exception:
        env.user_stats[(name, request_type)] = {
            "vehicles_count": 0,
            "clusters_count": 0,
        }
    else:
        if "map" in name:
            vehicles_count = sum(i["vehicles_count"] for i in response.json())
            clusters_count = len(response.json())
        else:
            vehicles_count = len(response.json())
            clusters_count = 0
        env.user_stats[(name, request_type)] = {
            "vehicles_count": vehicles_count,
            "clusters_count": clusters_count,
        }


class UserStatsWebUI(WebUI):
    def __init__(
        self,
        environment: "UserStatsEnvironment",  # CHANGED!
        host: str,
        port: int,
        auth_credentials: Optional[str] = None,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
        stats_csv_writer: Optional[StatsCSV] = None,
        delayed_start=False,
        userclass_picker_is_active=False,
    ):
        """
        Create WebUI instance and start running the web server in a separate greenlet (self.greenlet)

        Arguments:
        environment: Reference to the current Locust Environment
        host: Host/interface that the web server should accept connections to
        port: Port that the web server should listen to
        auth_credentials:  If provided, it will enable basic auth with all the routes protected by default.
                           Should be supplied in the format: "user:pass".
        tls_cert: A path to a TLS certificate
        tls_key: A path to a TLS private key
        delayed_start: Whether or not to delay starting web UI until `start()` is called. Delaying web UI start
                       allows for adding Flask routes or Blueprints before accepting requests, avoiding errors.
        """
        environment.web_ui = self
        self.stats_csv_writer = stats_csv_writer or StatsCSV(
            environment, stats_module.PERCENTILES_TO_REPORT
        )
        self.environment = environment
        self.host = host
        self.port = port
        self.tls_cert = tls_cert
        self.tls_key = tls_key
        self.userclass_picker_is_active = userclass_picker_is_active
        app = Flask(__name__)
        CORS(app)
        self.app = app
        app.jinja_env.add_extension("jinja2.ext.do")
        app.debug = True
        app.root_path = os.path.dirname(os.path.abspath(__file__))
        self.app.config["BASIC_AUTH_ENABLED"] = False
        self.auth: Optional[BasicAuth] = None
        self.greenlet: Optional[gevent.Greenlet] = None
        self._swarm_greenlet: Optional[gevent.Greenlet] = None
        self.template_args = {}

        if auth_credentials is not None:
            credentials = auth_credentials.split(":")
            if len(credentials) == 2:
                self.app.config["BASIC_AUTH_USERNAME"] = credentials[0]
                self.app.config["BASIC_AUTH_PASSWORD"] = credentials[1]
                self.app.config["BASIC_AUTH_ENABLED"] = True
                self.auth = BasicAuth()
                self.auth.init_app(self.app)
            else:
                raise AuthCredentialsError(
                    "Invalid auth_credentials. It should be a string in the following format: 'user:pass'"
                )
        if environment.runner:
            self.update_template_args()
        if not delayed_start:
            self.start()

        @app.route("/")
        @self.auth_required_if_enabled
        def index() -> str | Response:
            if not environment.runner:
                return make_response(
                    "Error: Locust Environment does not have any runner", 500
                )
            self.update_template_args()
            # Here we could replace template, if it wasn't hardcoded
            return render_template(LOCUST_INDEX_HTML, **self.template_args)

        @app.route("/swarm", methods=["POST"])
        @self.auth_required_if_enabled
        def swarm() -> Response:
            assert request.method == "POST"

            # Loading UserClasses & ShapeClasses if Locust is running with UserClass Picker
            if self.userclass_picker_is_active:
                if not self.environment.available_user_classes:
                    err_msg = "UserClass picker is active but there are no available UserClasses"
                    return jsonify(
                        {"success": False, "message": err_msg, "host": environment.host}
                    )

                # Getting Specified User Classes
                form_data_user_class_names = request.form.getlist("user_classes")

                # Updating UserClasses
                if form_data_user_class_names:
                    user_classes = {}
                    for (
                        user_class_name,
                        user_class_object,
                    ) in self.environment.available_user_classes.items():
                        if user_class_name in form_data_user_class_names:
                            user_classes[user_class_name] = user_class_object

                else:
                    if (
                        self.environment.runner
                        and self.environment.runner.state == STATE_RUNNING
                    ):
                        # Test is already running
                        # Using the user classes that have already been selected
                        user_classes = {
                            key: value
                            for (
                                key,
                                value,
                            ) in self.environment.available_user_classes.items()
                            if value in self.environment.user_classes
                        }
                    else:
                        # Starting test with no user class selection
                        # Defaulting to using all available user classes
                        user_classes = self.environment.available_user_classes

                self._update_user_classes(user_classes)

                # Updating ShapeClass if specified in WebUI Form
                form_data_shape_class_name = request.form.get("shape_class", "Default")
                if form_data_shape_class_name == "Default":
                    self._update_shape_class(None)
                else:
                    self._update_shape_class(form_data_shape_class_name)

            parsed_options_dict = (
                vars(environment.parsed_options) if environment.parsed_options else {}
            )
            run_time = None
            for key, value in request.form.items():
                if (
                    key == "user_count"
                ):  # if we just renamed this field to "users" we wouldn't need this
                    user_count = int(value)
                elif key == "spawn_rate":
                    spawn_rate = float(value)
                elif key == "host":
                    # Replace < > to guard against XSS
                    environment.host = (
                        str(request.form["host"]).replace("<", "").replace(">", "")
                    )
                elif key == "user_classes":
                    # Set environment.parsed_options.user_classes to the selected user_classes
                    parsed_options_dict[key] = request.form.getlist("user_classes")
                elif key == "run_time":
                    if not value:
                        continue
                    try:
                        run_time = parse_timespan(value)
                    except ValueError:
                        err_msg = "Valid run_time formats are : 20, 20s, 3m, 2h, 1h20m, 3h30m10s, etc."
                        logger.error(err_msg)
                        return jsonify(
                            {
                                "success": False,
                                "message": err_msg,
                                "host": environment.host,
                            }
                        )
                elif key in parsed_options_dict:
                    # update the value in environment.parsed_options, but dont change the type.
                    # This won't work for parameters that are None
                    parsed_options_dict[key] = type(parsed_options_dict[key])(value)

            if environment.shape_class and environment.runner is not None:
                environment.runner.start_shape()
                return jsonify(
                    {
                        "success": True,
                        "message": "Swarming started using shape class",
                        "host": environment.host,
                    }
                )

            if self._swarm_greenlet is not None:
                self._swarm_greenlet.kill(block=True)
                self._swarm_greenlet = None

            if environment.runner is not None:
                self._swarm_greenlet = gevent.spawn(
                    environment.runner.start, user_count, spawn_rate
                )
                self._swarm_greenlet.link_exception(greenlet_exception_handler)
                response_data = {
                    "success": True,
                    "message": "Swarming started",
                    "host": environment.host,
                }
                if run_time:
                    gevent.spawn_later(run_time, self._stop_runners).link_exception(
                        greenlet_exception_handler
                    )
                    response_data["run_time"] = run_time

                if self.userclass_picker_is_active:
                    response_data["user_classes"] = sorted(user_classes.keys())

                return jsonify(response_data)
            else:
                return jsonify(
                    {"success": False, "message": "No runner", "host": environment.host}
                )

        @app.route("/stop")
        @self.auth_required_if_enabled
        def stop() -> Response:
            if self._swarm_greenlet is not None:
                self._swarm_greenlet.kill(block=True)
                self._swarm_greenlet = None
            if environment.runner is not None:
                environment.runner.stop()
            return jsonify({"success": True, "message": "Test stopped"})

        @app.route("/stats/reset")
        @self.auth_required_if_enabled
        def reset_stats() -> str:
            environment.events.reset_stats.fire()
            if environment.runner is not None:
                environment.runner.stats.reset_all()
                environment.runner.exceptions = {}
            return "ok"

        @app.route("/stats/report")
        @self.auth_required_if_enabled
        def stats_report() -> Response:
            res = get_html_report(
                self.environment, show_download_link=not request.args.get("download")
            )
            if request.args.get("download"):
                res = app.make_response(res)
                res.headers[
                    "Content-Disposition"
                ] = f"attachment;filename=report_{time()}.html"
            return res

        def _download_csv_suggest_file_name(suggest_filename_prefix: str) -> str:
            """Generate csv file download attachment filename suggestion.

            Arguments:
            suggest_filename_prefix: Prefix of the filename to suggest for saving the download. Will be appended with timestamp.
            """

            return f"{suggest_filename_prefix}_{time()}.csv"

        def _download_csv_response(csv_data: str, filename_prefix: str) -> Response:
            """Generate csv file download response with 'csv_data'.

            Arguments:
            csv_data: CSV header and data rows.
            filename_prefix: Prefix of the filename to suggest for saving the download. Will be appended with timestamp.
            """

            response = make_response(csv_data)
            response.headers["Content-type"] = "text/csv"
            response.headers[
                "Content-disposition"
            ] = f"attachment;filename={_download_csv_suggest_file_name(filename_prefix)}"
            return response

        @app.route("/stats/requests/csv")
        @self.auth_required_if_enabled
        def request_stats_csv() -> Response:
            data = StringIO()
            writer = csv.writer(data)
            self.stats_csv_writer.requests_csv(writer)
            return _download_csv_response(data.getvalue(), "requests")

        @app.route("/stats/requests_full_history/csv")
        @self.auth_required_if_enabled
        def request_stats_full_history_csv() -> Response:
            options = self.environment.parsed_options
            if (
                options
                and options.stats_history_enabled
                and isinstance(self.stats_csv_writer, StatsCSVFileWriter)
            ):
                return send_file(
                    os.path.abspath(self.stats_csv_writer.stats_history_file_name()),
                    mimetype="text/csv",
                    as_attachment=True,
                    download_name=_download_csv_suggest_file_name(
                        "requests_full_history"
                    ),
                    etag=True,
                    max_age=0,
                    conditional=True,
                    last_modified=None,
                )

            return make_response(
                "Error: Server was not started with option to generate full history.",
                404,
            )

        @app.route("/stats/failures/csv")
        @self.auth_required_if_enabled
        def failures_stats_csv() -> Response:
            data = StringIO()
            writer = csv.writer(data)
            self.stats_csv_writer.failures_csv(writer)
            return _download_csv_response(data.getvalue(), "failures")

        @app.route("/stats/requests")
        @self.auth_required_if_enabled
        @memoize(timeout=DEFAULT_CACHE_TIME, dynamic_timeout=True)
        def request_stats() -> Response:
            stats: List[Dict[str, Any]] = []
            errors: List[StatsErrorDict] = []

            if environment.runner is None:
                report = {
                    "stats": stats,
                    "errors": errors,
                    "total_rps": 0.0,
                    "fail_ratio": 0.0,
                    "current_response_time_percentile_95": None,
                    "current_response_time_percentile_50": None,
                    "state": STATE_MISSING,
                    "user_count": 0,
                }

                if isinstance(environment.runner, MasterRunner):
                    report.update({"workers": []})

                return jsonify(report)

            for s in chain(
                sort_stats(environment.runner.stats.entries),
                [environment.runner.stats.total],
            ):
                stats.append(
                    {
                        "method": s.method,
                        "name": s.name,
                        "safe_name": escape(s.name, quote=False),
                        "num_requests": s.num_requests,
                        "num_failures": s.num_failures,
                        "avg_response_time": s.avg_response_time,
                        "min_response_time": 0
                        if s.min_response_time is None
                        else proper_round(s.min_response_time),
                        "max_response_time": proper_round(s.max_response_time),
                        "current_rps": s.current_rps,
                        "current_fail_per_sec": s.current_fail_per_sec,
                        "median_response_time": s.median_response_time,
                        "ninetieth_response_time": s.get_response_time_percentile(0.9),
                        "ninety_ninth_response_time": s.get_response_time_percentile(
                            0.99
                        ),
                        "avg_content_length": s.avg_content_length,
                        # ADDED: Pass data to response
                        **environment.user_stats.get((s.name, s.method), {}),
                    }
                )

            for e in environment.runner.errors.values():
                err_dict = e.serialize()
                err_dict["name"] = escape(err_dict["name"])
                err_dict["error"] = escape(err_dict["error"])
                errors.append(err_dict)

            # Truncate the total number of stats and errors displayed since a large number of rows will cause the app
            # to render extremely slowly. Aggregate stats should be preserved.
            truncated_stats = stats[:500]
            if len(stats) > 500:
                truncated_stats += [stats[-1]]

            report = {
                "stats": truncated_stats,
                "errors": errors[:500],
                #
                "user_stats_headers": list(
                    environment.user_stats_headers.keys()
                ),  # Keep order
            }

            if stats:
                report["total_rps"] = stats[len(stats) - 1]["current_rps"]
                report["fail_ratio"] = environment.runner.stats.total.fail_ratio
                report[
                    "current_response_time_percentile_95"
                ] = environment.runner.stats.total.get_current_response_time_percentile(
                    0.95
                )
                report[
                    "current_response_time_percentile_50"
                ] = environment.runner.stats.total.get_current_response_time_percentile(
                    0.5
                )

            if isinstance(environment.runner, MasterRunner):
                workers = []
                for worker in environment.runner.clients.values():
                    workers.append(
                        {
                            "id": worker.id,
                            "state": worker.state,
                            "user_count": worker.user_count,
                            "cpu_usage": worker.cpu_usage,
                            "memory_usage": worker.memory_usage,
                        }
                    )

                report["workers"] = workers

            report["state"] = environment.runner.state
            report["user_count"] = environment.runner.user_count

            return jsonify(report)

        @app.route("/exceptions")
        @self.auth_required_if_enabled
        def exceptions() -> Response:
            return jsonify(
                {
                    "exceptions": [
                        {
                            "count": row["count"],
                            "msg": escape(row["msg"]),
                            "traceback": escape(row["traceback"]),
                            "nodes": ", ".join(row["nodes"]),
                        }
                        for row in (
                            environment.runner.exceptions.values()
                            if environment.runner is not None
                            else []
                        )
                    ]
                }
            )

        @app.route("/exceptions/csv")
        @self.auth_required_if_enabled
        def exceptions_csv() -> Response:
            data = StringIO()
            writer = csv.writer(data)
            self.stats_csv_writer.exceptions_csv(writer)
            return _download_csv_response(data.getvalue(), "exceptions")

        @app.route("/tasks")
        @self.auth_required_if_enabled
        def tasks() -> Dict[str, Dict[str, Dict[str, float]]]:
            runner = self.environment.runner
            user_spawned: Dict[str, int]
            if runner is None:
                user_spawned = {}
            else:
                user_spawned = (
                    runner.reported_user_classes_count
                    if isinstance(runner, MasterRunner)
                    else runner.user_classes_count
                )

            task_data = {
                "per_class": get_ratio(
                    self.environment.user_classes, user_spawned, False
                ),
                "total": get_ratio(self.environment.user_classes, user_spawned, True),
            }
            return task_data

    def update_template_args(self):
        super().update_template_args()
        self.template_args["user_stats_headers"] = self.environment.user_stats_headers
        # Here locust uses https://github.com/efeminella/jqote2-template-loader,
        # we need pass formatted string
        self.template_args["js_user_stats_rows"] = "\n".join(
            [
                f"<td><%= this.{name} || '-' %></td>"
                for name in self.environment.user_stats_headers
            ]
        )


class UserStatsEnvironment(Environment):
    user_stats = None
    user_stats_headers = None

    def __init__(
        self,
        *,
        user_classes=None,
        shape_class=None,
        tags=None,
        locustfile: str = None,
        exclude_tags=None,
        events=None,
        host=None,
        reset_stats=False,
        stop_timeout=None,
        catch_exceptions=True,
        parsed_options=None,
        available_user_classes=None,
        available_shape_classes=None,
    ):
        super().__init__(
            user_classes=user_classes,
            shape_class=shape_class,
            tags=tags,
            locustfile=locustfile,
            exclude_tags=exclude_tags,
            events=events,
            host=host,
            reset_stats=reset_stats,
            stop_timeout=stop_timeout,
            catch_exceptions=catch_exceptions,
            parsed_options=parsed_options,
            available_user_classes=available_user_classes,
            available_shape_classes=available_shape_classes,
        )
        self.user_stats = {}
        self.user_stats_headers = {
            "vehicles_count": "Points Count",
            "clusters_count": "Clusters Count",
        }

    def create_web_ui(
        self,
        host="",
        port=8089,
        auth_credentials=None,
        tls_cert=None,
        tls_key=None,
        stats_csv_writer=None,
        delayed_start=False,
        userclass_picker_is_active=False,
    ) -> UserStatsWebUI:
        self.web_ui = UserStatsWebUI(
            self,
            host,
            port,
            auth_credentials=auth_credentials,
            tls_cert=tls_cert,
            tls_key=tls_key,
            stats_csv_writer=stats_csv_writer,
            delayed_start=delayed_start,
            userclass_picker_is_active=userclass_picker_is_active,
        )
        return self.web_ui


class WebsiteUser(FastHttpUser):
    wait_time = between(5, 10)
    network_timeout = 10
    connection_timeout = 10
    host = "http://localhost:8000"

    def get_filter(self):
        min_lat_filter = uniform(min_lat, min_lat + 0.189)
        max_lat_filter = uniform(max_lat, max_lat - 0.189)
        min_lon_filter = uniform(min_lon, min_lon - 0.19)
        max_lon_filter = uniform(max_lon, max_lon + 0.19)
        return f"min_lat={min_lat_filter}&max_lat={max_lat_filter}&min_lon={min_lon_filter}&max_lon={max_lon_filter}"

    @task
    def list_paginated(self):
        self.client.get("/api/vehicles/")

    @tag("js")
    @task
    def js_clustering(self):
        filter_str = self.get_filter()
        self.client.get(f"/api/vehicles/js_clustering/?{filter_str}")

    @tag("slow")
    @task
    def slow_map(self):
        filter_str = self.get_filter()
        self.client.get(f"/api/vehicles/map/?{filter_str}")

    @tag("fast")
    @task
    def fast_map(self):
        filter_str = self.get_filter()
        self.client.get(
            f"/api/vehicles/map_fast/?{filter_str}",
        )


def main(tags):
    global env
    # setup Environment and Runner
    env = UserStatsEnvironment(
        user_classes=[WebsiteUser],
        events=events,
        locustfile="Clustering Django",
        tags=tags or None,
    )
    runner = env.create_local_runner()

    # start a WebUI instance
    web_ui = env.create_web_ui("0.0.0.0", 8089)

    # execute init event handlers (only really needed if you have registered any)
    env.events.init.fire(environment=env, runner=runner, web_ui=web_ui)

    # start a greenlet that periodically outputs the current stats
    gevent.spawn(stats_printer(env.stats))

    # start a greenlet that save current stats to history
    gevent.spawn(stats_history, env.runner)

    # start the test
    runner.start(1, spawn_rate=10)

    # in 60 seconds stop the runner
    gevent.spawn_later(60, lambda: runner.quit())

    # wait for the greenlets
    runner.greenlet.join()

    # stop the web server for good measures
    web_ui.stop()


def init_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("tags", nargs="*")
    return parser


if __name__ == "__main__":
    parser = init_parser()
    args = parser.parse_args()
    main(args.tags)
