from ..tfstatereader import extract

INSTANCE = r"""
{
    "version": 3,
    "terraform_version": "0.7.4",
    "serial": 108,
    "lineage": "79cc5f6a-b3b7-4b86-93e6-987ae7f373eb",
    "remote": {
        "type": "s3",
        "config": {
            "bucket": "datawire-terraform",
            "key": "managed-infrastructure",
            "region": "us-east-1"
        }
    },
    "modules": [{
        "path": [
            "root",
            "mcp_postgres_dev"
        ],
        "outputs": {},
        "resources": {
            "aws_db_instance.main": {
                "type": "aws_db_instance",
                "depends_on": [
                    "aws_db_subnet_group.main"
                ],
                "primary": {
                    "id": "mcp-develop",
                    "attributes": {
                        "address": "mcp-develop.crhykb8ijynb.us-east-1.rds.amazonaws.com",
                        "allocated_storage": "10",
                        "allow_major_version_upgrade": "true",
                        "arn": "arn:aws:rds:us-east-1:914373874199:db:mcp-develop",
                        "auto_minor_version_upgrade": "true",
                        "availability_zone": "us-east-1c",
                        "backup_retention_period": "0",
                        "backup_window": "04:34-05:04",
                        "copy_tags_to_snapshot": "false",
                        "db_subnet_group_name": "mcp-develop",
                        "endpoint": "mcp-develop.crhykb8ijynb.us-east-1.rds.amazonaws.com:5432",
                        "engine": "postgres",
                        "engine_version": "9.6.1",
                        "id": "mcp-develop",
                        "identifier": "mcp-develop",
                        "instance_class": "db.t2.micro",
                        "iops": "0",
                        "kms_key_id": "",
                        "license_model": "postgresql-license",
                        "maintenance_window": "fri:05:42-fri:06:12",
                        "monitoring_interval": "0",
                        "multi_az": "false",
                        "name": "",
                        "option_group_name": "default:postgres-9-6",
                        "parameter_group_name": "default.postgres9.6",
                        "password": "REDACTED_PASSWORD",
                        "port": "5432",
                        "publicly_accessible": "false",
                        "replicas.#": "0",
                        "replicate_source_db": "",
                        "security_group_names.#": "0",
                        "skip_final_snapshot": "true",
                        "status": "available",
                        "storage_encrypted": "false",
                        "storage_type": "gp2",
                        "tags.%": "1",
                        "tags.pib_metadata": "{ \"app\":\"datawire\", \"resource_name\":\"postgres96\" }",
                        "username": "REDACTED_USERNAME",
                        "vpc_security_group_ids.#": "1",
                        "vpc_security_group_ids.548992056": "sg-d43d90a9"
                    },
                    "meta": {},
                    "tainted": false
                },
                "deposed": [],
                "provider": ""
            }
        },
        "depends_on": []
    }, {
        "path": [
            "root",
            "tracing_es_develop"
        ],
        "outputs": {
            "elasticsearch_arn": {
                "sensitive": false,
                "type": "string",
                "value": "arn:aws:es:us-east-1:914373874199:domain/tracing-develop"
            },
            "elasticsearch_domain_id": {
                "sensitive": false,
                "type": "string",
                "value": "914373874199/tracing-develop"
            },
            "elasticsearch_endpoint": {
                "sensitive": false,
                "type": "string",
                "value": "search-tracing-develop-oprqwhmnjzz75m6gy4eh3x6yqy.us-east-1.es.amazonaws.com"
            }
        },
        "resources": {
            "aws_elasticsearch_domain.elasticsearch": {
                "type": "aws_elasticsearch_domain",
                "depends_on": [
                    "data.template_file.policy"
                ],
                "primary": {
                    "id": "arn:aws:es:us-east-1:914373874199:domain/tracing-develop",
                    "attributes": {
                        "access_policies": "{\"Statement\":[{\"Action\":\"es:*\",\"Condition\":{\"IpAddress\":{\"aws:SourceIp\":\"0.0.0.0\"}},\"Effect\":\"Allow\",\"Principal\":\"*\",\"Resource\":\"arn:aws:es:us-east-1:914373874199:domain/tracing-develop/*\"}],\"Version\":\"2012-10-17\"}",
                        "advanced_options.%": "1",
                        "advanced_options.rest.action.multi.allow_explicit_index": "true",
                        "arn": "arn:aws:es:us-east-1:914373874199:domain/tracing-develop",
                        "cluster_config.#": "1",
                        "cluster_config.0.dedicated_master_count": "2",
                        "cluster_config.0.dedicated_master_enabled": "true",
                        "cluster_config.0.dedicated_master_type": "t2.small.elasticsearch",
                        "cluster_config.0.instance_count": "2",
                        "cluster_config.0.instance_type": "t2.small.elasticsearch",
                        "cluster_config.0.zone_awareness_enabled": "true",
                        "domain_id": "914373874199/tracing-develop",
                        "domain_name": "tracing-develop",
                        "ebs_options.#": "1",
                        "ebs_options.0.ebs_enabled": "true",
                        "ebs_options.0.iops": "0",
                        "ebs_options.0.volume_size": "20",
                        "ebs_options.0.volume_type": "gp2",
                        "elasticsearch_version": "2.3",
                        "endpoint": "search-tracing-develop-oprqwhmnjzz75m6gy4eh3x6yqy.us-east-1.es.amazonaws.com",
                        "id": "arn:aws:es:us-east-1:914373874199:domain/tracing-develop",
                        "snapshot_options.#": "1",
                        "snapshot_options.0.automated_snapshot_start_hour": "0",
                        "tags.%": "1",
                        "tags.pib_metadata": "{ \"app\":\"datawire\", \"service\":\"trace\", \"resource_name\":\"es\" }"
                    },
                    "meta": {},
                    "tainted": false
                },
                "deposed": [],
                "provider": ""
            }
        },
        "depends_on": []
    }, {
        "path": [
            "root",
            "tracing_es_prod"
        ],
        "outputs": {
            "elasticsearch_arn": {
                "sensitive": false,
                "type": "string",
                "value": "arn:aws:es:us-east-1:914373874199:domain/tracing-prod"
            },
            "elasticsearch_domain_id": {
                "sensitive": false,
                "type": "string",
                "value": "914373874199/tracing-prod"
            },
            "elasticsearch_endpoint": {
                "sensitive": false,
                "type": "string",
                "value": "search-tracing-prod-jtw3midcw72dvqpciz3mufifkm.us-east-1.es.amazonaws.com"
            }
        },
        "resources": {
            "aws_elasticsearch_domain.elasticsearch": {
                "type": "aws_elasticsearch_domain",
                "depends_on": [
                    "data.template_file.policy"
                ],
                "primary": {
                    "id": "arn:aws:es:us-east-1:914373874199:domain/tracing-prod",
                    "attributes": {
                        "access_policies": "{\"Statement\":[{\"Action\":\"es:*\",\"Condition\":{\"IpAddress\":{\"aws:SourceIp\":\"0.0.0.0\"}},\"Effect\":\"Allow\",\"Principal\":\"*\",\"Resource\":\"arn:aws:es:us-east-1:914373874199:domain/tracing-prod/*\"}],\"Version\":\"2012-10-17\"}",
                        "advanced_options.%": "1",
                        "advanced_options.rest.action.multi.allow_explicit_index": "true",
                        "arn": "arn:aws:es:us-east-1:914373874199:domain/tracing-prod",
                        "cluster_config.#": "1",
                        "cluster_config.0.dedicated_master_count": "2",
                        "cluster_config.0.dedicated_master_enabled": "true",
                        "cluster_config.0.dedicated_master_type": "m3.medium.elasticsearch",
                        "cluster_config.0.instance_count": "2",
                        "cluster_config.0.instance_type": "m3.medium.elasticsearch",
                        "cluster_config.0.zone_awareness_enabled": "true",
                        "domain_id": "914373874199/tracing-prod",
                        "domain_name": "tracing-prod",
                        "ebs_options.#": "1",
                        "ebs_options.0.ebs_enabled": "true",
                        "ebs_options.0.iops": "0",
                        "ebs_options.0.volume_size": "20",
                        "ebs_options.0.volume_type": "gp2",
                        "elasticsearch_version": "2.3",
                        "endpoint": "search-tracing-prod-jtw3midcw72dvqpciz3mufifkm.us-east-1.es.amazonaws.com",
                        "id": "arn:aws:es:us-east-1:914373874199:domain/tracing-prod",
                        "snapshot_options.#": "1",
                        "snapshot_options.0.automated_snapshot_start_hour": "0",
                        "tags.%": "0"
                    },
                    "meta": {},
                    "tainted": false
                },
                "deposed": [],
                "provider": ""
            }
        },
        "depends_on": []
    }]
}
"""


def test_extract():
    extracted = extract(INSTANCE)
    assert 2 == extracted.size()  # because the above JSON has a resource which will not be injected


def test_unregistered_type_is_skipped():
    data = r"""{
    "version": 3,
    "terraform_version": "0.7.4",
    "serial": 108,
    "lineage": "79cc5f6a-b3b7-4b86-93e6-987ae7f373eb",
    "modules": [{
        "path": [
            "root",
            "mcp_postgres_dev"
        ],
        "outputs": {},
        "resources": {
            "aws_db_instance.main": {
                "type": "aws_db_NOTREALLYATYPE",
                "depends_on": [
                    "aws_db_subnet_group.main"
                ],
                "primary": {
                    "id": "mcp-develop",
                    "attributes": {
                        "address": "mcp-develop.crhykb8ijynb.us-east-1.rds.amazonaws.com",
                        "allocated_storage": "10",
                        "allow_major_version_upgrade": "true",
                        "arn": "arn:aws:rds:us-east-1:914373874199:db:mcp-develop",
                        "auto_minor_version_upgrade": "true",
                        "availability_zone": "us-east-1c",
                        "backup_retention_period": "0",
                        "backup_window": "04:34-05:04",
                        "copy_tags_to_snapshot": "false",
                        "db_subnet_group_name": "mcp-develop",
                        "endpoint": "mcp-develop.crhykb8ijynb.us-east-1.rds.amazonaws.com:5432",
                        "engine": "postgres",
                        "engine_version": "9.6.1",
                        "id": "mcp-develop",
                        "identifier": "mcp-develop",
                        "instance_class": "db.t2.micro",
                        "iops": "0",
                        "kms_key_id": "",
                        "license_model": "postgresql-license",
                        "maintenance_window": "fri:05:42-fri:06:12",
                        "monitoring_interval": "0",
                        "multi_az": "false",
                        "name": "",
                        "option_group_name": "default:postgres-9-6",
                        "parameter_group_name": "default.postgres9.6",
                        "password": "REDACTED_PASSWORD",
                        "port": "5432",
                        "publicly_accessible": "false",
                        "replicas.#": "0",
                        "replicate_source_db": "",
                        "security_group_names.#": "0",
                        "skip_final_snapshot": "true",
                        "status": "available",
                        "storage_encrypted": "false",
                        "storage_type": "gp2",
                        "tags.%": "1",
                        "tags.pib_metadata": "{ \"app\":\"datawire\", \"resource_name\":\"postgres96\" }",
                        "username": "REDACTED_USERNAME",
                        "vpc_security_group_ids.#": "1",
                        "vpc_security_group_ids.548992056": "sg-d43d90a9"
                    },
                    "meta": {},
                    "tainted": false
                },
                "deposed": [],
                "provider": ""
            }
        },
        "depends_on": []
    }]}"""

    extracted = extract(data)
    assert 0 == extracted.size()


def test_no_metadata_is_skipped():
    data = r"""{
    "version": 3,
    "terraform_version": "0.7.4",
    "serial": 108,
    "lineage": "79cc5f6a-b3b7-4b86-93e6-987ae7f373eb",
    "modules": [{
        "path": [
            "root",
            "mcp_postgres_dev"
        ],
        "outputs": {},
        "resources": {
            "aws_db_instance.main": {
                "type": "aws_db_instance",
                "depends_on": [
                    "aws_db_subnet_group.main"
                ],
                "primary": {
                    "id": "mcp-develop",
                    "attributes": {
                        "address": "mcp-develop.crhykb8ijynb.us-east-1.rds.amazonaws.com",
                        "allocated_storage": "10",
                        "allow_major_version_upgrade": "true",
                        "arn": "arn:aws:rds:us-east-1:914373874199:db:mcp-develop",
                        "auto_minor_version_upgrade": "true",
                        "availability_zone": "us-east-1c",
                        "backup_retention_period": "0",
                        "backup_window": "04:34-05:04",
                        "copy_tags_to_snapshot": "false",
                        "db_subnet_group_name": "mcp-develop",
                        "endpoint": "mcp-develop.crhykb8ijynb.us-east-1.rds.amazonaws.com:5432",
                        "engine": "postgres",
                        "engine_version": "9.6.1",
                        "id": "mcp-develop",
                        "identifier": "mcp-develop",
                        "instance_class": "db.t2.micro",
                        "iops": "0",
                        "kms_key_id": "",
                        "license_model": "postgresql-license",
                        "maintenance_window": "fri:05:42-fri:06:12",
                        "monitoring_interval": "0",
                        "multi_az": "false",
                        "name": "",
                        "option_group_name": "default:postgres-9-6",
                        "parameter_group_name": "default.postgres9.6",
                        "password": "REDACTED_PASSWORD",
                        "port": "5432",
                        "publicly_accessible": "false",
                        "replicas.#": "0",
                        "replicate_source_db": "",
                        "security_group_names.#": "0",
                        "skip_final_snapshot": "true",
                        "status": "available",
                        "storage_encrypted": "false",
                        "storage_type": "gp2",
                        "tags.%": "0",
                        "username": "REDACTED_USERNAME",
                        "vpc_security_group_ids.#": "1",
                        "vpc_security_group_ids.548992056": "sg-d43d90a9"
                    },
                    "meta": {},
                    "tainted": true
                },
                "deposed": [],
                "provider": ""
            }
        },
        "depends_on": []
    }]}"""

    extracted = extract(data)
    assert 0 == extracted.size()


def test_tainted_is_skipped():

    data = r"""{
    "version": 3,
    "terraform_version": "0.7.4",
    "serial": 108,
    "lineage": "79cc5f6a-b3b7-4b86-93e6-987ae7f373eb",
    "modules": [{
        "path": [
            "root",
            "mcp_postgres_dev"
        ],
        "outputs": {},
        "resources": {
            "aws_db_instance.main": {
                "type": "aws_db_instance",
                "depends_on": [
                    "aws_db_subnet_group.main"
                ],
                "primary": {
                    "id": "mcp-develop",
                    "attributes": {
                        "address": "mcp-develop.crhykb8ijynb.us-east-1.rds.amazonaws.com",
                        "allocated_storage": "10",
                        "allow_major_version_upgrade": "true",
                        "arn": "arn:aws:rds:us-east-1:914373874199:db:mcp-develop",
                        "auto_minor_version_upgrade": "true",
                        "availability_zone": "us-east-1c",
                        "backup_retention_period": "0",
                        "backup_window": "04:34-05:04",
                        "copy_tags_to_snapshot": "false",
                        "db_subnet_group_name": "mcp-develop",
                        "endpoint": "mcp-develop.crhykb8ijynb.us-east-1.rds.amazonaws.com:5432",
                        "engine": "postgres",
                        "engine_version": "9.6.1",
                        "id": "mcp-develop",
                        "identifier": "mcp-develop",
                        "instance_class": "db.t2.micro",
                        "iops": "0",
                        "kms_key_id": "",
                        "license_model": "postgresql-license",
                        "maintenance_window": "fri:05:42-fri:06:12",
                        "monitoring_interval": "0",
                        "multi_az": "false",
                        "name": "",
                        "option_group_name": "default:postgres-9-6",
                        "parameter_group_name": "default.postgres9.6",
                        "password": "REDACTED_PASSWORD",
                        "port": "5432",
                        "publicly_accessible": "false",
                        "replicas.#": "0",
                        "replicate_source_db": "",
                        "security_group_names.#": "0",
                        "skip_final_snapshot": "true",
                        "status": "available",
                        "storage_encrypted": "false",
                        "storage_type": "gp2",
                        "tags.%": "1",
                        "tags.pib_metadata": "{ \"app\":\"datawire\", \"resource_name\":\"postgres96\" }",
                        "username": "REDACTED_USERNAME",
                        "vpc_security_group_ids.#": "1",
                        "vpc_security_group_ids.548992056": "sg-d43d90a9"
                    },
                    "meta": {},
                    "tainted": true
                },
                "deposed": [],
                "provider": ""
            }
        },
        "depends_on": []
    }]}"""

    extracted = extract(data)
    assert 0 == extracted.size()


def test_render():

    data = r"""{
    "version": 3,
    "terraform_version": "0.7.4",
    "serial": 108,
    "lineage": "79cc5f6a-b3b7-4b86-93e6-987ae7f373eb",
    "modules": [{
        "path": [
            "root",
            "mcp_postgres_dev"
        ],
        "outputs": {},
        "resources": {
            "aws_db_instance.main": {
                "type": "aws_db_instance",
                "depends_on": [
                    "aws_db_subnet_group.main"
                ],
                "primary": {
                    "id": "mcp-develop",
                    "attributes": {
                        "address": "mcp-develop.crhykb8ijynb.us-east-1.rds.amazonaws.com",
                        "allocated_storage": "10",
                        "allow_major_version_upgrade": "true",
                        "arn": "arn:aws:rds:us-east-1:914373874199:db:mcp-develop",
                        "auto_minor_version_upgrade": "true",
                        "availability_zone": "us-east-1c",
                        "backup_retention_period": "0",
                        "backup_window": "04:34-05:04",
                        "copy_tags_to_snapshot": "false",
                        "db_subnet_group_name": "mcp-develop",
                        "endpoint": "mcp-develop.crhykb8ijynb.us-east-1.rds.amazonaws.com:5432",
                        "engine": "postgres",
                        "engine_version": "9.6.1",
                        "id": "mcp-develop",
                        "identifier": "mcp-develop",
                        "instance_class": "db.t2.micro",
                        "iops": "0",
                        "kms_key_id": "",
                        "license_model": "postgresql-license",
                        "maintenance_window": "fri:05:42-fri:06:12",
                        "monitoring_interval": "0",
                        "multi_az": "false",
                        "name": "",
                        "option_group_name": "default:postgres-9-6",
                        "parameter_group_name": "default.postgres9.6",
                        "password": "REDACTED_PASSWORD",
                        "port": "5432",
                        "publicly_accessible": "false",
                        "replicas.#": "0",
                        "replicate_source_db": "",
                        "security_group_names.#": "0",
                        "skip_final_snapshot": "true",
                        "status": "available",
                        "storage_encrypted": "false",
                        "storage_type": "gp2",
                        "tags.%": "1",
                        "tags.pib_metadata": "{ \"app\":\"datawire\", \"resource_name\":\"postgres96\" }",
                        "username": "REDACTED_USERNAME",
                        "vpc_security_group_ids.#": "1",
                        "vpc_security_group_ids.548992056": "sg-d43d90a9"
                    },
                    "meta": {},
                    "tainted": false
                },
                "deposed": [],
                "provider": ""
            }
        },
        "depends_on": []
    }]}"""

    extracted = extract(data)
    assert 1 == extracted.size()
