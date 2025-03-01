import os
import time
import shutil

from xcpcio_board_spider import logger, Contest, Teams, Submissions, constants, utils
from xcpcio_board_spider.type import Image
from xcpcio_board_spider.spider.domjudge.v3.domjudge import DOMjudge

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
ASSETS_PATH = "../ecfinal-assets"

ENABLE_FROZEN = os.getenv("ENABLE_FROZEN", "true").lower() == "true"
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "")

log = logger.init_logger()


def get_basic_contest():
    c = Contest()
    c.logo = Image(preset="ICPC")
    c.banner = Image(
        url="{}/banner_min.png".format(ASSETS_PATH))

    return c


def handle_teams(teams: Teams):
    filter_team_ids = []

    for team in teams.values():
        d_team = team.extra[DOMjudge.CONSTANT_EXTRA_DOMJUDGE_TEAM]

        if "participants" in d_team["group_ids"]:
            team.official = True
        elif "observers" in d_team["group_ids"]:
            team.unofficial = True
        else:
            filter_team_ids.append(team.team_id)
            continue

        if "public_description" in d_team.keys() and d_team["public_description"] is not None:
            description = d_team["public_description"]

            members = description.split(", ")
            team.members = members[:3]
            if len(members) > 3:
                team.coach = members[3]
                team.coach = team.coach.replace("(教练)", "")

        if team.name.startswith("⭐"):
            team.name = team.name.replace("⭐", "")

    for team_id in filter_team_ids:
        del teams[team_id]


def is_frozen(c: Contest):
    unfrozen_time = 0

    if c.unfrozen_time <= 86400:
        unfrozen_time = c.end_time + c.unfrozen_time
    else:
        unfrozen_time = c.unfrozen_time

    if ENABLE_FROZEN and utils.get_now_timestamp_second() <= unfrozen_time:
        return True

    return False


def handle_runs(c: Contest, runs: Submissions):
    t = utils.get_timestamp_second(
        c.end_time) - utils.get_timestamp_second(c.start_time) - c.frozen_time
    t = t * 1000

    for run in runs:
        run.time = None

        if is_frozen(c):
            if run.status == constants.RESULT_ACCEPTED:
                pass
            elif run.status == constants.RESULT_COMPILATION_ERROR:
                pass
            elif run.status == constants.RESULT_PENDING:
                pass
            else:
                run.status = constants.RESULT_REJECTED

            if run.timestamp >= t:
                run.status = constants.RESULT_FROZEN


def write_to_disk(data_dir: str, c: Contest, teams: Teams, runs: Submissions, if_not_exists=False):
    log.info("write to disk. [data_dir: {}]".format(data_dir))

    utils.ensure_makedirs(data_dir)

    utils.output(os.path.join(data_dir, "config.json"),
                 c.get_dict)
    utils.output(os.path.join(data_dir, "team.json"),
                 teams.get_dict, if_not_exists=if_not_exists)
    utils.output(os.path.join(data_dir, "run.json"),
                 runs.get_dict, if_not_exists=if_not_exists)


def copy_assets(data_dir: str):
    try:
        assets_path = os.path.join(CUR_DIR, "assets")
        target_path = os.path.join(data_dir, ASSETS_PATH)
        if os.path.exists(assets_path) and os.path.isdir(assets_path):
            if os.path.exists(target_path) and os.path.isdir(target_path):
                shutil.rmtree(target_path)
            shutil.copytree(assets_path, target_path)
    except Exception as e:
        log.error("copy assets failed. ", e)


def work(data_dir: str, c: Contest, fetch_uri: str):
    utils.ensure_makedirs(data_dir)
    write_to_disk(data_dir, c, Teams(), Submissions(), True)

    copy_assets(data_dir)

    if len(SECRET_TOKEN) > 0:
        write_to_disk(data_dir + SECRET_TOKEN, c, Teams(), Submissions(), True)

    if len(fetch_uri) == 0:
        return

    d = DOMjudge(c, fetch_uri)

    while True:
        log.info("loop start")

        try:
            d.fetch().update_contest().parse_teams().parse_runs()

            handle_teams(d.teams)

            if len(SECRET_TOKEN) > 0:
                write_to_disk(data_dir + SECRET_TOKEN, c, d.teams, d.runs)

            handle_runs(c, d.runs)
            write_to_disk(data_dir, c, d.teams, d.runs)

            log.info("work successfully")
        except Exception as e:
            log.error("work failed. ", e)

        log.info("sleeping...")
        time.sleep(1)
