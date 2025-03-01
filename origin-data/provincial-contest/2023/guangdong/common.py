import os
import time

from xcpcio_board_spider import logger, Contest, Teams, Submissions, constants, logo, utils
from xcpcio_board_spider.spider.csg_cpc.v1 import CSG_CPC

log = logger.init_logger()


def get_basic_contest():
    c = Contest()

    c.frozen_time = 60 * 60
    c.penalty = 20 * 60
    c.organization = "School"

    c.group = {
        constants.TEAM_TYPE_OFFICIAL: constants.TEAM_TYPE_ZH_CN_OFFICIAL,
        constants.TEAM_TYPE_UNOFFICIAL: constants.TEAM_TYPE_ZH_CH_UNOFFICIAL,
        constants.TEAM_TYPE_GIRL: constants.TEAM_TYPE_ZH_CH_GIRL,
    }

    c.status_time_display = {
        constants.RESULT_CORRECT: 1,
        constants.RESULT_INCORRECT: 1,
        constants.RESULT_PENDING: 1,
    }

    c.logo = logo.CCPC

    return c


def handle_teams(teams: Teams):
    for team in teams.values():
        if team.official == True:
            team.official = 1

        if team.unofficial == True:
            team.unofficial = 1

        if team.girl == True:
            team.girl = 1


def handle_runs(runs: Submissions, problem_id_base: int):
    for run in runs:
        run.problem_id -= problem_id_base


def work(data_dir: str, c: Contest, team_uris, run_uris, problem_id_base: int):
    utils.ensure_makedirs(data_dir)
    utils.output(os.path.join(data_dir, "config.json"), c.get_dict)
    utils.output(os.path.join(data_dir, "team.json"), {}, True)
    utils.output(os.path.join(data_dir, "run.json"), [], True)

    while True:
        log.info("loop start")

        try:
            csg_cpc = CSG_CPC(c, team_uris, run_uris)
            csg_cpc.fetch().parse_teams().parse_runs()

            handle_teams(csg_cpc.teams)
            handle_runs(csg_cpc.runs, problem_id_base)

            utils.output(os.path.join(data_dir, "config.json"), c.get_dict)
            utils.output(os.path.join(data_dir, "team.json"),
                         csg_cpc.teams.get_dict)
            utils.output(os.path.join(data_dir, "run.json"),
                         csg_cpc.runs.get_dict)

            log.info("work successfully")
        except Exception as e:
            log.error("work failed. ", e)

        log.info("sleeping...")
        time.sleep(1)
