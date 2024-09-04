import dotenv
import psycopg
import pytest

dotenv.load_dotenv()


def does_test_user_exist(cur: psycopg.Cursor) -> bool:
    cur.execute("""
        select count(*) > 0
        from pg_catalog.pg_roles
        where rolname = 'test'
    """)
    return cur.fetchone()[0]


def create_test_user(cur: psycopg.Cursor) -> None:
    if not does_test_user_exist(cur):
        cur.execute("create user test password 'test'")


def does_test_db_exist(cur: psycopg.Cursor) -> bool:
    cur.execute("""
        select count(*) > 0
        from pg_catalog.pg_database
        where datname = 'test'
    """)
    return cur.fetchone()[0]


def drop_pg_cron_if_exists(cur: psycopg.Cursor) -> None:
    cur.execute("select count(*) > 0 from pg_extension where extname = 'pg_cron'")
    if cur.fetchone()[0] is True:
        cur.execute("select cron.unschedule(jobid) from cron.job")
    cur.execute("drop extension if exists pg_cron cascade")


def drop_test_db(cur: psycopg.Cursor) -> None:
    cur.execute("select pg_terminate_backend(pid) from pg_stat_activity where datname = 'test'")
    cur.execute("drop database test with (force)")


def create_test_db(cur: psycopg.Cursor) -> None:
    if does_test_db_exist(cur):
        drop_test_db(cur)
    cur.execute("create database test owner test")


@pytest.fixture(scope="session", autouse=True)
def set_up_test_db() -> None:
    with psycopg.connect(f"postgres://postgres@127.0.0.1:5432/postgres", autocommit=True) as con:
        with con.cursor() as cur:
            create_test_user(cur)
            if does_test_db_exist(cur):
                # drop the pg_cron extension from the test database, so we can kill all the connections to test database
                with psycopg.connect(f"postgres://postgres@127.0.0.1:5432/test") as con2:
                    with con2.cursor() as cur2:
                        drop_pg_cron_if_exists(cur2)
            create_test_db(cur)
    with psycopg.connect(f"postgres://postgres@127.0.0.1:5432/test", autocommit=True) as con:
        with con.cursor() as cur:
            cur.execute("grant execute on function pg_read_binary_file(text) to test")
            cur.execute("grant pg_read_server_files to test")
    with psycopg.connect(f"postgres://test@127.0.0.1:5432/test") as con:
        with con.cursor() as cur:
            cur.execute("create extension ai cascade")


@pytest.fixture(scope="session", autouse=True)
def load_dotenv() -> None:
    dotenv.load_dotenv()
