from pib import deploy


def test_filter_environments():
    cases = [
        (
            {'local': {}},
            {}
        ),
        (
            {'local': {},
             'remote0': {'auto_deploy': False},
             'remote1': {'auto_deploy': True}},

            {'remote1': deploy.Environment('remote1', {'auto_deploy': True})}
        )
    ]

    for case in cases:
        actual, expected = case
        assert deploy.filter_environments({'environments': actual}) == expected


def test_sanity():
    # tuple format = (environment, stack, is_sane)
    cases = [
        # Case 1 => Doesn't depend on anything
        (
            deploy.Environment('remote0', {'components': {
                'named-component-1': {},
                'named-component-2': {}
            }}),

            deploy.Stack({'name': 'case1', 'requires': []}),
            True
        ),

        # Case 2 => Depends on something defined.
        (
            deploy.Environment('remote0', {'components': {
                'named-component-1': {},
                'named-component-2': {}
            }}),

            deploy.Stack({'name': 'case2', 'requires': ['named-component-1', 'named-component-2']}),
            True
        ),

        # Case 3 => Depends on something not defined.
        (
            deploy.Environment('remote0', {'components': {
                'named-component-1': {},
                'named-component-2': {}
            }}),

            deploy.Stack({'name': 'case1', 'requires': ['named-component-1', 'UNDEFINED-COMPONENT']}),
            False
        )
    ]

    for case in cases:
        env, stack, result = case
        print("---")
        print("env  = {}".format(env))
        print("stack = {}".format(stack))
        print("expected = {}".format(result))
        print("---")
        assert deploy.sanity(env, stack) == result
