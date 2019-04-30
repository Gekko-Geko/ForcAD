import json
from typing import List

import storage
from helpers import models, rating
from storage import caching


def get_teams() -> List[models.Team]:
    """Get list of teams registered in the database"""
    with storage.get_redis_storage().pipeline(transaction=True) as pipeline:
        cached, = pipeline.exists('teams:cached').execute()
        if not cached:
            caching.cache_teams()

        teams, = pipeline.smembers('teams').execute()
        teams = list(models.Team.from_json(team) for team in teams)

    return teams


def get_team_id_by_token(token: str) -> int:
    """Get team by token

        :param token: token string
        :return: team id
    """
    with storage.get_redis_storage().pipeline(transaction=True) as pipeline:
        cached, = pipeline.exists('teams:cached').execute()
        if not cached:
            caching.cache_teams()

        team_id, = pipeline.get(f'team:token:{token}').execute()

    return team_id


def handle_attack(attacker_id: int, victim_id: int, task_id: int) -> float:
    """Recalculate team ratings and publish redis message

        :param attacker_id: id of the attacking team
        :param victim_id: id of the victim team
        :param task_id: id of task which is attacked
    """

    conn = storage.get_db_pool().getconn()
    curs = conn.cursor()

    query = "SELECT score from teamtasks WHERE team_id=%s AND task_id=%s"
    curs.execute(query, (attacker_id, task_id))
    attacker_score, = curs.fetchone()

    query = "SELECT score from teamtasks WHERE team_id=%s AND task_id=%s"
    curs.execute(query, (victim_id, task_id))
    victim_score, = curs.fetchone()

    rs = rating.RatingSystem(attacker=attacker_score, victim=victim_score)
    attacker_delta, victim_delta = rs.calculate()

    query = "UPDATE teamtasks SET score = %s WHERE team_id=%s AND task_id=%s"
    curs.execute(query, (attacker_score + attacker_delta, attacker_id, task_id))

    query = "UPDATE teamtasks SET score = %s WHERE team_id=%s AND task_id=%s"
    curs.execute(query, (victim_score + victim_delta, victim_id, task_id))

    conn.commit()
    curs.close()

    storage.get_db_pool().putconn(conn)

    flag_data = {
        'attacker_id': attacker_id,
        'victim_id': victim_id,
        'attacker_delta': attacker_delta,
        'victim_delta': victim_delta,
    }

    with storage.get_redis_storage().pipeline() as pipeline:
        pipeline.publish('flag_stolen', json.dumps(flag_data))

    return attacker_delta
