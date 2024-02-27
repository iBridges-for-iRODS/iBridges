import irods

from ibridges.resources import Resources


def test_resources(session, config):
    resources = Resources(session)
    resc_dict = resources.resources(update=True)
    assert list(resc_dict) == config["resources"]
    for i_resc, resc_name in enumerate(list(resc_dict)):
        if config["free_resources"][i_resc]:
            assert resources.get_free_space(resc_name) > 0
        resc = resources.get_resource(resc_name)
        assert isinstance(resc, irods.resource.iRODSResource)
