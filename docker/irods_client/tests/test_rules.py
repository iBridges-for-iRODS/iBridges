from ibridges.rules import execute_rule


def test_rules(session, testdata):
    rule_fp = str(testdata/"example.r")
    execute_rule(session, rule_fp, {})
    execute_rule(session, rule_fp, {'*in': 4, '*another_val': '"Value"'})
