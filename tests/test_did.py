import json
import os
import pytest
import re

from did.did import DID, SignatureType, PurposeType, ENTRY_SCHEMA_VERSION, \
    DID_METHOD_SPEC_VERSION, DID_METHOD_NAME
from did.encryptor import decrypt_keys_from_str, decrypt_keys_from_json, decrypt_keys_from_ui_store_file
from did.enums import EntryType


@pytest.fixture
def did():
    return DID()


class TestEmptyDid():
    def test_generating_new_empty_did(self, did):
        assert re.search("^{}:[a-f0-9]{{64}}$".format(DID_METHOD_NAME), did.id)
        assert 64 == len(did.nonce)
        assert [] == did.management_keys
        assert [] == did.did_keys
        assert [] == did.services
        assert set() == did.used_key_aliases
        assert set() == did.used_service_aliases


class TestManagementKeys():
    def test_add_management_keys(self, did):
        management_key_1_alias = 'management-key-1'
        management_key_1_priority = 1
        did.add_management_key(management_key_1_alias, management_key_1_priority)
        generated_management_key_1 = did.management_keys[0]

        assert management_key_1_alias == generated_management_key_1.alias
        assert management_key_1_priority == generated_management_key_1.priority
        assert SignatureType.EdDSA.value == generated_management_key_1.signature_type
        assert did.id == generated_management_key_1.controller
        assert generated_management_key_1.public_key is not None
        assert generated_management_key_1.private_key is not None

        management_key_2_alias = 'management-key-2'
        management_key_2_priority = 2
        management_key_2_signature_type = SignatureType.ECDSA.value
        management_key_2_controller = \
            '{}:d3936b2f0bdd45fe71d7156e835434b7970afd78868076f56654d05f838b8005'.format(DID_METHOD_NAME)

        did.add_management_key(management_key_2_alias, management_key_2_priority,
                               management_key_2_signature_type, management_key_2_controller)
        generated_management_key_2 = did.management_keys[1]

        assert management_key_2_alias == generated_management_key_2.alias
        assert management_key_2_priority == generated_management_key_2.priority
        assert management_key_2_signature_type == generated_management_key_2.signature_type
        assert management_key_2_controller == generated_management_key_2.controller
        assert generated_management_key_2.public_key is not None
        assert generated_management_key_2.private_key is not None

        management_key_3_alias = 'management-key-3'
        management_key_3_priority = 3
        management_key_3_signature_type = SignatureType.RSA.value

        did.add_management_key(management_key_3_alias, management_key_3_priority, management_key_3_signature_type)
        generated_management_key_3 = did.management_keys[2]

        assert management_key_3_alias == generated_management_key_3.alias
        assert management_key_3_priority == generated_management_key_3.priority
        assert management_key_3_signature_type == generated_management_key_3.signature_type
        assert did.id == generated_management_key_3.controller
        assert generated_management_key_3.public_key is not None
        assert generated_management_key_3.private_key is not None
        assert 3 == len(did.management_keys)

    def test_invalid_alias_throws_exception(self, did):
        test_cases = ['myManagementKey', 'my-m@nagement-key', 'my_management_key']
        for alias in test_cases:
            with pytest.raises(ValueError):
                did.add_management_key(alias, 1)

    def test_invalid_priority_throws_exception(self, did):
        test_cases = [-1, -2]
        for priority in test_cases:
            management_key_alias = 'management-key-{}'.format(str(priority))
            with pytest.raises(ValueError):
                did.add_management_key(management_key_alias, priority)

    def test_used_alias_throws_exception(self, did):
        management_key_alias = 'management-key-1'
        did.add_management_key(management_key_alias, 1)
        with pytest.raises(ValueError):
            did.add_management_key(management_key_alias, 1)

    def test_invalid_signature_type_throws_exception(self, did):
        management_key_alias = 'management-key'
        management_key_signature_type = 'invalid_signature_type'
        with pytest.raises(ValueError):
            did.add_management_key(management_key_alias, 1,
                                                                          management_key_signature_type)

    def test_invalid_controller_throws_exception(self, did):
        test_cases = [
            ('management-key-1', '{}:d3936b2f0bdd45fe71d7156e835434b7970afd78868076f56654h05f838b8005'.format(DID_METHOD_NAME)),
            ('management-key-2', 'did:fctr:d3936b2f0bdd45fe71d7156e835434b7970afd78868076f56654d05f838b8005'),
            ('management-key-3', '{}:d3936b2f0bdd45fe71d7156e835434b7970afd78868076f56654d05f838b800'.format(DID_METHOD_NAME))
        ]

        for alias, controller in test_cases:
            with pytest.raises(ValueError):
                did.add_management_key(alias, 1, SignatureType.EdDSA.value, controller)


class DidKeysTestCase():
    def test_add_did_keys(self, did):
        did_key_1_alias = 'did-key-1'
        did_key_1_purpose = [PurposeType.PublicKey.value]
        did.add_did_key(did_key_1_alias, did_key_1_purpose)
        generated_did_key_1 = did.did_keys[0]

        assert did_key_1_alias == generated_did_key_1.alias
        assert set(did_key_1_purpose) == generated_did_key_1.purpose
        assert SignatureType.EdDSA.value == generated_did_key_1.signature_type
        assert did.id == generated_did_key_1.controller
        assert None == generated_did_key_1.priority_requirement

        did_key_2_alias = 'did-key-2'
        did_key_2_purpose = [PurposeType.PublicKey.value, PurposeType.AuthenticationKey.value]
        did_key_2_signature_type = SignatureType.ECDSA.value
        did_key_2_controller = '{}:d3936b2f0bdd45fe71d7156e835434b7970afd78868076f56654d05f838b8005'.format(DID_METHOD_NAME)
        did_key_2_priority_requirement = 1
        did.add_did_key(did_key_2_alias, did_key_2_purpose, did_key_2_signature_type, did_key_2_controller,
                             did_key_2_priority_requirement)
        generated_did_key_2 = did.did_keys[1]

        assert did_key_2_alias == generated_did_key_2.alias
        assert set(did_key_2_purpose) == generated_did_key_2.purpose
        assert did_key_2_signature_type == generated_did_key_2.signature_type
        assert did_key_2_controller == generated_did_key_2.controller
        assert did_key_2_priority_requirement == generated_did_key_2.priority_requirement
        assert 2 == len(did.did_keys)

    def test_invalid_alias_throws_exception(self, did):
        test_cases = ['myDidKey', 'my-d!d-key', 'my_did_key']
        for alias in test_cases:
            with pytest.raises(ValueError):
                did.add_did_key(alias, [PurposeType.PublicKey.value])

    def test_invalid_purpose_type_throws_exception(self):
        did_key_alias = 'did-key'
        did_key_purpose = [PurposeType.PublicKey.value, 'InvalidPurposeType']
        with pytest.raises(ValueError):
            did.add_did_key(did_key_alias, did_key_purpose)

    def test_used_alias_throws_exception(self):
        alias = 'my-key-1'
        did.add_management_key(alias, 1)
        with pytest.raises(ValueError):
            did.add_did_key(alias, [PurposeType.PublicKey.value])

    def test_invalid_signature_type_throws_exception(self):
        did_key_alias = 'management-key'
        did_key_signature_type = 'invalid_signature_type'
        with pytest.raises(ValueError):
            did.add_did_key(did_key_alias, [PurposeType.PublicKey.value],
                                                                          did_key_signature_type)

    def test_invalid_controller_throws_exception(self):
        test_cases = [
            ('did-key-1', 'did:d3936b2f0bdd45fe71d7156e835434b7970afd78868076f56654d05f838b8005'),
            ('did-key-2', 'did:fctr:d3936b2f0bdd45fe71d7156e835434b7970afd78868076f56654d05f838b800')
        ]

        for alias, controller in test_cases:
            with pytest.raises(ValueError):
                did.add_did_key(alias, [PurposeType.PublicKey.value], SignatureType.EdDSA.value, controller)

    def test_invalid_priority_requirement_throws_exception(self):
        test_cases = [-1, -2]
        for priority_requirement in test_cases:
            did_key_alias = 'did-key-{}'.format(str(priority_requirement))
            with pytest.raises(ValueError):
                did.add_did_key(did_key_alias, [PurposeType.PublicKey.value],
                                SignatureType.EdDSA.value, None, priority_requirement)


class TestService():
    def test_add_service(self, did):
        service_1_alias = 'photo-service'
        service_1_type = 'PhotoStreamService'
        service_1_endpoint = 'https://myphoto.com'
        did.add_service(service_1_alias, service_1_type, service_1_endpoint)
        generated_service_1 = did.services[0]

        assert service_1_alias == generated_service_1.alias
        assert service_1_type == generated_service_1.service_type
        assert service_1_endpoint == generated_service_1.endpoint
        assert generated_service_1.priority_requirement is None

        service_2_alias = 'auth-service'
        service_2_type = 'AuthenticationService'
        service_2_endpoint = 'https://authenticateme.com'
        service_2_priority_requirement = 2
        did.add_service(service_2_alias, service_2_type, service_2_endpoint, service_2_priority_requirement)
        generated_service_2 = did.services[1]

        assert service_2_alias == generated_service_2.alias
        assert service_2_type == generated_service_2.service_type
        assert service_2_endpoint == generated_service_2.endpoint
        assert service_2_priority_requirement == generated_service_2.priority_requirement
        assert 2 == len(did.services)

    def test_invalid_alias_throws_exception(self, did):
        service_type = 'PhotoStreamService'
        service_endpoint = 'https://myphoto.com'
        test_cases = ['myPhotoService', 'my-ph@to-service', 'my_photo_service']
        for alias in test_cases:
            with pytest.raises(ValueError):
                did.add_service(alias, service_type, service_endpoint)

    def test_used_alias_throws_exception(self, did):
        service_alias = 'my-photo-service'
        service_type = 'PhotoStreamService'
        service_endpoint = 'https://myphoto.com'
        did.add_service(service_alias, service_type, service_endpoint)
        with pytest.raises(ValueError):
            did.add_service(service_alias, service_type, service_endpoint)

    def test_empty_service_type_throws_exception(self, did):
        service_alias = 'my-photo-service'
        service_type = ''
        service_endpoint = 'https://myphoto.com'
        with pytest.raises(ValueError):
            did.add_service(service_alias, service_type, service_endpoint)

    def test_invalid_endpoint_throws_exception(self, did):
        service_type = 'PhotoStreamService'
        test_cases = [
            ('service-1', 'myservice.com'),
            ('service-2', 'https//myphoto.com')
        ]

        for alias, endpoint in test_cases:
            with pytest.raises(ValueError):
                did.add_service(alias, service_type, endpoint)

    def test_invalid_priority_requirement_throws_exception(self, did):
        service_type = 'PhotoStreamService'
        service_endpoint = 'https://myphoto.com'
        test_cases = [-1, -2]
        for priority_requirement in test_cases:
            service_alias = 'service-{}'.format(str(priority_requirement))
            with pytest.raises(ValueError):
                did.add_service(service_alias, service_type, service_endpoint, priority_requirement)


class TestExportEntryData():
    def test_export_entry_data_returns_correct_ext_ids(self, did):
        did.add_management_key('my-management-key', 0)
        entry_data = did.export_entry_data()

        ext_ids = entry_data['ext_ids']
        assert EntryType.Create.value == ext_ids[0]
        assert ENTRY_SCHEMA_VERSION == ext_ids[1]
        assert did.nonce == ext_ids[2]

    def test_export_entry_data_with_management_key(self, did):
        key_alias = 'my-management-key'
        key_priority = 0
        did.add_management_key(key_alias, key_priority)
        entry_data = did.export_entry_data()

        content = json.loads(entry_data['content'])
        assert DID_METHOD_SPEC_VERSION == content['didMethodVersion']

        management_keys = content['managementKey']
        assert 1 == len(management_keys)
        with pytest.raises(KeyError):
            content['didKey']
        with pytest.raises(KeyError):
            content['service']

        management_key_1 = management_keys[0]
        assert '{}#{}'.format(did.id, key_alias) == management_key_1['id']
        assert '{}VerificationKey'.format(SignatureType.EdDSA.value) == management_key_1['type']
        assert did.id == management_key_1['controller']
        assert str(did.management_keys[0].public_key, 'utf8') == management_key_1['publicKeyBase58']
        assert key_priority == management_key_1['priority']

    def test_export_entry_data_with_did_key_and_service(self, did):
        did_key_alias = 'my-public-key'
        did_key_purpose = [PurposeType.PublicKey.value]
        did_key_signature_type = SignatureType.RSA.value
        did_key_controller = '{}:d3936b2f0bdd45fe71d7156e835434b7970afd78868076f56654d05f838b8005'.format(DID_METHOD_NAME)
        did_key_priority_requirement = 1
        service_alias = 'my-photo-service'
        service_type = 'PhotoStreamService'
        service_endpoint = 'https://myphoto.com'
        service_priority_requirement = 2
        did.add_management_key('my-management-key-1', 0)
        did.add_management_key('my-management-key-2', 2)
        did.add_did_key(did_key_alias, did_key_purpose, did_key_signature_type, did_key_controller,
                             did_key_priority_requirement)
        did.add_service(service_alias, service_type, service_endpoint, service_priority_requirement)
        entry_data = did.export_entry_data()
        content = json.loads(entry_data['content'])

        management_keys = content['managementKey']
        did_keys = content['didKey']
        services = content['service']
        assert 2 == len(management_keys)
        assert 1 == len(did_keys)
        assert 1 == len(services)

        did_key_1 = did_keys[0]
        assert '{}#{}'.format(did.id, did_key_alias) == did_key_1['id']
        assert '{}VerificationKey'.format(did_key_signature_type) == did_key_1['type']
        assert did_key_controller == did_key_1['controller']
        assert str(did.did_keys[0].public_key, 'utf8') == did_key_1['publicKeyPem']
        assert did_key_purpose == did_key_1['purpose']
        assert did_key_priority_requirement == did_key_1['priorityRequirement']

        service_1 = services[0]
        assert '{}#{}'.format(did.id, service_alias) == service_1['id']
        assert service_type == service_1['type']
        assert service_endpoint == service_1['serviceEndpoint']
        assert service_priority_requirement == service_1['priorityRequirement']

    def test_exceed_entry_size_throws_error(self, did):
        for x in range(0, 35):
            did.add_management_key('management-key-{}'.format(x), 0)

        with pytest.raises(ValueError):
            did.export_entry_data()

    def test_export_without_management_key_throws_error(self, did):
        with pytest.raises(ValueError):
            did.export_entry_data()