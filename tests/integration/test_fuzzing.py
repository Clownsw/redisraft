import random
import logging
import redis
from nose.tools import eq_
from nose.plugins.attrib import attr

from test_tools import with_setup_args
import sandbox


def _setup():
    return [sandbox.Cluster()], {}


def _teardown(c):
    c.destroy()


@attr('fuzz')
@with_setup_args(_setup, _teardown)
def test_fuzzing_with_restarts(c):
    """
    Basic Raft fuzzer test
    """

    nodes = 3
    cycles = 100

    c.create(nodes)
    for i in range(cycles):
        eq_(c.raft_exec('INCRBY', 'counter', 1), i + 1)
        logging.info('---------- Executed INCRBY # %s', i)
        if i % 7 == 0:
            r = random.randint(1, nodes)
            logging.info('********** Restarting node %s **********', r)
            c.node(r).restart()
            c.node(r).wait_for_election()
            logging.info('********** Node %s is UP **********', r)

    eq_(int(c.raft_exec('GET', 'counter')), cycles)


@attr('fuzz')
@with_setup_args(_setup, _teardown)
def test_fuzzing_with_restarts_and_rewrites(c):
    """
    Counter fuzzer with log rewrites.
    """

    nodes = 3
    cycles = 100

    c.create(nodes)
    # Randomize max log entries
    for node in c.nodes.values():
        node.client.execute_command(
            'RAFT.CONFIG', 'SET', 'raft-log-max-file-size',
            str(random.randint(1000, 2000)))

    for i in range(cycles):
        eq_(c.raft_exec('INCRBY', 'counter', 1), i + 1)
        logging.info('---------- Executed INCRBY # %s', i)
        if random.randint(1, 7) == 1:
            r = random.randint(1, nodes)
            logging.info('********** Restarting node %s **********', r)
            c.node(r).restart()
            c.node(r).wait_for_election()
            logging.info('********** Node %s is UP **********', r)

    eq_(int(c.raft_exec('GET', 'counter')), cycles)


@attr('fuzz')
@with_setup_args(_setup, _teardown)
def test_fuzzing_with_config_changes(c):
    """
    Basic Raft fuzzer test
    """

    nodes = 5
    cycles = 100

    c.create(nodes)
    for i in range(cycles):
        eq_(c.raft_exec('INCRBY', 'counter', 1), i + 1)
        if random.randint(1, 7) == 1:
            try:
                node_id = c.random_node_id()
                c.remove_node(node_id)
            except redis.ResponseError:
                continue
            c.add_node().wait_for_node_voting()

    eq_(int(c.raft_exec('GET', 'counter')), cycles)