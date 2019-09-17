import json

import pytest

from client.did import DID, DIDKeyPurpose, SignatureType


@pytest.fixture
def empty_did():
    return DID()


@pytest.fixture
def did():
    return DID().management_key("man-key1", 0)


@pytest.fixture
def full_did():
    return (
        DID()
        .management_key("man-key1", 0)
        .management_key("man-key2", 1, SignatureType.ECDSA.value)
        .management_key("man-key3", 1)
        .management_key("man-key4", 2, SignatureType.RSA.value)
        .did_key(
            "did-key1", DIDKeyPurpose.AuthenticationKey.value, priority_requirement=2
        )
        .did_key(
            "did-key2",
            [DIDKeyPurpose.AuthenticationKey.value, DIDKeyPurpose.PublicKey.value],
            priority_requirement=3,
        )
        .did_key("did-key3", DIDKeyPurpose.PublicKey.value, priority_requirement=1)
        .service("gmail-service", "email-service", "https://gmail.com", 2)
        .service(
            "banking-credential-service",
            "credential-store-service",
            "https://credentials.com",
            0,
        )
    )


def test_update_with_empty_did(empty_did):
    with pytest.raises(RuntimeError):
        empty_did.update()


class TestManagementKeys:
    def test_management_key_addition(self, did):
        updated = did.update().add_management_key("man-key2", 1).get_updated()
        assert len(updated.management_keys) == 2
        assert updated.management_keys[0] != updated.management_keys[1]
        assert updated.management_keys[1].alias == "man-key2"
        assert updated.management_keys[1].priority == 1

    def test_management_key_revocation(self, full_did):
        updated = (
            full_did.update()
            .revoke_management_key("man-key1")
            .revoke_management_key("man-key4")
            .get_updated()
        )
        assert len(updated.management_keys) == 2
        for key in updated.management_keys:
            assert key.alias not in {"man-key1", "man-key4"}
            assert key.alias in {"man-key2", "man-key3"}


class TestDIDKeys:
    def test_did_key_addition(self, did):
        updated = (
            did.update()
            .add_did_key("did-key1", DIDKeyPurpose.AuthenticationKey.value)
            .get_updated()
        )
        assert len(updated.management_keys) == 1
        assert len(updated.did_keys) == 1
        assert updated.did_keys[0].alias == "did-key1"
        assert updated.did_keys[0].purpose == ["authentication"]

    def test_did_key_revocation(self, full_did):
        updated = full_did.update().revoke_did_key("did-key2").get_updated()
        assert len(updated.did_keys) == 2
        for key in updated.did_keys:
            assert key.alias is not "did-key2"
            assert key.alias in {"did-key1", "did-key3"}


class TestServices:
    def test_service_addition(self, did):
        updated = (
            did.update()
            .add_service("service-1", "email-service", "https://gmail.com")
            .get_updated()
        )
        assert len(updated.services) == 1
        assert updated.services[0].alias == "service-1"
        assert updated.services[0].service_type == "email-service"
        assert updated.services[0].endpoint == "https://gmail.com"

    def test_service_revocation(self, full_did):
        updated = full_did.update().revoke_service("Gmail-service").get_updated()
        assert len(updated.services) == 2
        updated = (
            updated.update()
            .revoke_service("gmail-service")
            .revoke_service("banking-credential-service")
            .get_updated()
        )
        assert len(updated.services) == 0


class TestExportUpdateEntryData:
    def test_no_changes(self, full_did):
        assert full_did.update().export_entry_data() is None

    def test_only_additions(self, did):
        update_entry = (
            did.update()
            .add_management_key("man-key2", 0)
            .add_management_key("man-key3", 1, signature_type=SignatureType.RSA.value)
            .add_did_key(
                "did-key1",
                purpose=DIDKeyPurpose.PublicKey.value,
                priority_requirement=1,
            )
            .add_service(
                "signature-service",
                "signature-service",
                "https://signature-service.com",
            )
            .export_entry_data()
        )

        ext_ids = update_entry["ext_ids"]
        content = json.loads(update_entry["content"])

        assert ext_ids[0] == "DIDUpdate".encode("utf-8")
        assert ext_ids[1] == "1.0.0".encode("utf-8")
        assert ext_ids[2] == "{}#{}".format(did.id, "man-key1").encode("utf-8")
        assert len(ext_ids) == 4
        assert "revoke" not in content

        added = content["add"]
        assert len(added["managementKey"]) == 2
        assert len(added["didKey"]) == 1
        assert len(added["service"]) == 1

        for key in added["managementKey"]:
            assert key["controller"] == did.id
            id_parts = key["id"].split("#")
            did_id = id_parts[0]
            alias = id_parts[1]
            assert did_id == did.id
            assert alias in {"man-key2", "man-key3"}
            if alias == "man-key2":
                assert key["type"] == "Ed25519VerificationKey"
                assert key["priority"] == 0
                assert "publicKeyBase58" in key
                assert "publicKeyPem" not in key
                assert "priorityRequirement" not in key
            else:
                assert key["type"] == "RSAVerificationKey"
                assert key["priority"] == 1
                assert "publicKeyPem" in key
                assert "publicKeyBase58" not in key
                assert "priorityRequirement" not in key

        new_did_key = added["didKey"][0]
        assert new_did_key["id"] == "{}#{}".format(did.id, "did-key1")
        assert new_did_key["purpose"] == ["publicKey"]
        assert new_did_key["priorityRequirement"] == 1
        assert new_did_key["type"] == "Ed25519VerificationKey"
        assert new_did_key["controller"] == did.id

        new_service = added["service"][0]
        assert new_service["id"] == "{}#{}".format(did.id, "signature-service")
        assert new_service["type"] == "signature-service"
        assert new_service["serviceEndpoint"] == "https://signature-service.com"

    def test_only_revocation(self, full_did):
        update_entry = (
            full_did.update()
            .revoke_management_key("man-key3")
            .revoke_did_key("did-key2")
            .revoke_service("gmail-service")
            .export_entry_data()
        )

        ext_ids = update_entry["ext_ids"]
        content = json.loads(update_entry["content"])

        assert ext_ids[0] == "DIDUpdate".encode("utf-8")
        assert ext_ids[1] == "1.0.0".encode("utf-8")
        assert ext_ids[2] == "{}#{}".format(full_did.id, "man-key1").encode("utf-8")
        assert len(ext_ids) == 4
        assert "add" not in content

        revoked = content["revoke"]
        assert len(revoked["managementKey"]) == 1
        assert len(revoked["didKey"]) == 1
        assert len(revoked["service"]) == 1
        assert revoked["managementKey"][0]["id"] == "man-key3"
        assert revoked["didKey"][0]["id"] == "did-key2"
        assert revoked["service"][0]["id"] == "gmail-service"

    def test_addition_and_revocation(self, full_did):
        update_entry = (
            full_did.update()
            .add_management_key("man-key5", 0)
            .add_did_key("auth-key1", DIDKeyPurpose.AuthenticationKey.value)
            .add_service(
                "encrypted-chat", "chat-service", "https://my-chat-service.com"
            )
            .revoke_management_key("man-key1")
            .revoke_did_key("did-key3")
            .revoke_did_key("did-key1")
            .revoke_service("gmail-service")
            .export_entry_data()
        )

        ext_ids = update_entry["ext_ids"]
        content = json.loads(update_entry["content"])

        assert ext_ids[0] == "DIDUpdate".encode("utf-8")
        assert ext_ids[1] == "1.0.0".encode("utf-8")
        assert ext_ids[2] == "{}#{}".format(full_did.id, "man-key1").encode("utf-8")
        assert len(ext_ids) == 4
        assert "add" in content
        assert "revoke" in content

        revoked = content["revoke"]
        assert len(revoked["managementKey"]) == 1
        assert len(revoked["didKey"]) == 2
        assert len(revoked["service"]) == 1
        assert revoked["managementKey"][0]["id"] == "man-key1"
        assert revoked["didKey"][0]["id"] in {"did-key1", "did-key3"}
        assert revoked["didKey"][1]["id"] in {"did-key1", "did-key3"}
        assert revoked["service"][0]["id"] == "gmail-service"

        added = content["add"]
        assert len(added["managementKey"]) == 1
        assert len(added["didKey"]) == 1
        assert len(added["service"]) == 1

        assert added["managementKey"][0]["id"] == "{}#man-key5".format(full_did.id)
        assert added["managementKey"][0]["priority"] == 0

        assert added["didKey"][0]["id"] == "{}#auth-key1".format(full_did.id)
        assert added["didKey"][0]["purpose"] == ["authentication"]

        assert added["service"][0]["id"] == "{}#encrypted-chat".format(full_did.id)
        assert added["service"][0]["type"] == "chat-service"
        assert added["service"][0]["serviceEndpoint"] == "https://my-chat-service.com"
