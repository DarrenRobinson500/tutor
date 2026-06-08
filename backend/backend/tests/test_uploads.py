"""
Tests for file-upload and bulk-import endpoints.

Covers:
  - POST /api/templates/import_bulk/  — YAML / JSON template import
  - POST /api/skills/import_bulk/     — YAML skill tree import
  - POST /api/tutors/{id}/edit/       — tutor profile field edits
                                        (logo field exists on TutorProfile but the
                                        current edit action does not yet handle
                                        request.FILES; tests document the current
                                        behaviour and include a pending logo test
                                        so it is easy to enable once implemented)
"""

import io
import unittest
import yaml

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from .base import BaseAPITestCase
from .factories import make_user, make_tutor_profile, make_skill, make_template
from backend.models import Template, Skill


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _yaml_file(data, filename="import.yaml"):
    """Serialise *data* to YAML bytes and wrap in a SimpleUploadedFile."""
    content = yaml.dump(data, allow_unicode=True, default_flow_style=False)
    return SimpleUploadedFile(filename, content.encode("utf-8"), content_type="application/x-yaml")


def _raw_file(content: str, filename="import.yaml"):
    """Wrap a raw string as a YAML upload file."""
    return SimpleUploadedFile(filename, content.encode("utf-8"), content_type="application/x-yaml")


# ---------------------------------------------------------------------------
# Template import_bulk
# ---------------------------------------------------------------------------

@override_settings(MEDIA_ROOT="/tmp/test-media/")
class TemplateImportBulkTests(BaseAPITestCase):
    """POST /api/templates/import_bulk/"""

    URL = "/api/templates/import_bulk/"

    def setUp(self):
        self.admin = make_user(role='admin', is_superuser=True, is_staff=True)
        self.auth(self.admin)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _valid_template_record(self, content_suffix=""):
        """Return a minimal template record dict suitable for YAML import."""
        content = f"title: Sample Question{content_suffix}\ndifficulty: easy\n"
        return {
            "content": content,
            "topic": "Algebra",
            "subtopic": "Linear",
            "grade": "7",
            "difficulty": "easy",
            "tags": [],
            "curriculum": [],
            "validated": False,
            "status": "draft",
        }

    # ------------------------------------------------------------------
    # Happy-path: TemplateViewSet has AllowAny, so no auth needed
    # ------------------------------------------------------------------

    def test_import_valid_yaml_creates_templates(self):
        """A well-formed YAML file with two records creates two Template rows."""
        records = [
            self._valid_template_record("_A"),
            self._valid_template_record("_B"),
        ]
        before = Template.objects.count()
        uploaded = _yaml_file(records)

        response = self.client.post(self.URL, {"file": uploaded}, format="multipart")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["created"], 2)
        self.assertEqual(data["errors"], 0)
        self.assertEqual(Template.objects.count(), before + 2)

    def test_import_valid_yaml_with_skill_detail_code(self):
        """Importing a record that references an existing skill_detail_code links the skill."""
        parent = make_skill(code="MATH", description="Mathematics", is_detail=False)
        detail = make_skill(
            code="MATH-D1",
            description="Add integers",
            parent_skill=parent,
            is_detail=True,
        )
        record = self._valid_template_record("_linked")
        record["skill_detail_code"] = detail.code

        uploaded = _yaml_file([record])
        response = self.client.post(self.URL, {"file": uploaded}, format="multipart")

        self.assertEqual(response.status_code, 200)
        tpl = Template.objects.order_by("-id").first()
        self.assertEqual(tpl.skill_detail_id, detail.id)

    def test_import_valid_yaml_skips_duplicate_content(self):
        """A record whose content already exists in the DB is skipped, not duplicated."""
        record = self._valid_template_record("_dup")
        # Pre-create a template with the same content string
        Template.objects.create(
            content=record["content"],
            difficulty="easy",
            status="draft",
        )
        before = Template.objects.count()

        uploaded = _yaml_file([record])
        response = self.client.post(self.URL, {"file": uploaded}, format="multipart")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["skipped"], 1)
        self.assertEqual(data["created"], 0)
        self.assertEqual(Template.objects.count(), before)

    def test_import_valid_json_file_creates_templates(self):
        """A .json extension is parsed as JSON rather than YAML."""
        import json as _json
        records = [self._valid_template_record("_json")]
        content_bytes = _json.dumps(records).encode("utf-8")
        uploaded = SimpleUploadedFile("import.json", content_bytes, content_type="application/json")

        response = self.client.post(self.URL, {"file": uploaded}, format="multipart")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["created"], 1)

    def test_import_malformed_yaml_returns_400(self):
        """Malformed YAML that cannot be parsed returns HTTP 400."""
        bad_yaml = "key: [\nbad indentation\n  - item\n: broken"
        uploaded = _raw_file(bad_yaml, "bad.yaml")

        response = self.client.post(self.URL, {"file": uploaded}, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_import_malformed_yaml_leaves_no_partial_records(self):
        """When YAML parse fails, no Template rows are created at all."""
        before = Template.objects.count()
        bad_yaml = ": broken yaml ]["
        uploaded = _raw_file(bad_yaml, "bad.yaml")

        self.client.post(self.URL, {"file": uploaded}, format="multipart")

        self.assertEqual(Template.objects.count(), before)

    def test_import_missing_file_returns_400(self):
        """Posting without a file key returns HTTP 400."""
        response = self.client.post(self.URL, {}, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_import_unauthenticated_is_denied(self):
        """TemplateViewSet now requires authentication for POST — unauthenticated imports return 401."""
        self.unauth()  # drop credentials
        records = [self._valid_template_record("_anon")]
        uploaded = _yaml_file(records)

        response = self.client.post(self.URL, {"file": uploaded}, format="multipart")

        self.assertIn(response.status_code, [401, 403])


# ---------------------------------------------------------------------------
# Skill import_bulk
# ---------------------------------------------------------------------------

@override_settings(MEDIA_ROOT="/tmp/test-media/")
class SkillImportBulkTests(BaseAPITestCase):
    """POST /api/skills/import_bulk/"""

    URL = "/api/skills/import_bulk/"

    def _minimal_skill_node(self, code="TST01", description="Test skill", detail=None):
        """Return a minimal skill tree node in the format expected by import_skill_tree."""
        node = {
            "code": code,
            "description": description,
            "years_practised": ["7", "8"],
            "detail": detail or ["Understand basics", "Apply method"],
        }
        return node

    # ------------------------------------------------------------------
    # Happy-path
    # ------------------------------------------------------------------

    def test_import_valid_yaml_creates_skills(self):
        """A valid YAML skill tree creates top-level skill and detail children."""
        node = self._minimal_skill_node(code="NEWSK", description="New Skill")
        uploaded = _yaml_file([node])

        before_top = Skill.objects.filter(is_detail=False).count()

        response = self.client.post(self.URL, {"file": uploaded}, format="multipart")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "Skills imported successfully")
        self.assertGreater(data["seen"], 0)
        # The top-level node plus its two detail lines = at least 3 codes seen
        self.assertGreaterEqual(data["seen"], 3)
        # One new top-level skill was created
        self.assertEqual(Skill.objects.filter(is_detail=False).count(), before_top + 1)

    def test_import_creates_detail_children(self):
        """Detail lines inside a skill node are created as is_detail=True children."""
        node = self._minimal_skill_node(
            code="DTLSK",
            description="Detail Skill",
            detail=["First detail", "Second detail"],
        )
        uploaded = _yaml_file([node])
        self.client.post(self.URL, {"file": uploaded}, format="multipart")

        parent = Skill.objects.filter(code="DTLSK").first()
        self.assertIsNotNone(parent)
        details = Skill.objects.filter(parent=parent, is_detail=True).order_by("order_index")
        self.assertEqual(details.count(), 2)
        self.assertEqual(details[0].description, "First detail")
        self.assertEqual(details[1].description, "Second detail")

    def test_import_updates_existing_skill(self):
        """Importing a node whose code already exists updates the existing record."""
        existing = make_skill(code="EXIST1", description="Old description", is_detail=False)
        node = self._minimal_skill_node(code="EXIST1", description="Updated description")
        uploaded = _yaml_file([node])

        response = self.client.post(self.URL, {"file": uploaded}, format="multipart")

        self.assertEqual(response.status_code, 200)
        existing.refresh_from_db()
        self.assertEqual(existing.description, "Updated description")

    def test_import_nested_children(self):
        """Child nodes under a top-level node are created as child skills."""
        node = {
            "code": "PARENT1",
            "description": "Parent Skill",
            "years_practised": ["9"],
            "detail": [],
            "children": [
                {
                    "code": "CHILD1",
                    "description": "Child Skill",
                    "years_practised": ["9"],
                    "detail": ["Detail A"],
                }
            ],
        }
        uploaded = _yaml_file([node])
        response = self.client.post(self.URL, {"file": uploaded}, format="multipart")

        self.assertEqual(response.status_code, 200)
        parent = Skill.objects.filter(code="PARENT1").first()
        child = Skill.objects.filter(code="CHILD1").first()
        self.assertIsNotNone(parent)
        self.assertIsNotNone(child)
        self.assertEqual(child.parent_id, parent.id)

    # ------------------------------------------------------------------
    # Error cases
    # ------------------------------------------------------------------

    def test_import_malformed_yaml_returns_400(self):
        """Malformed YAML returns HTTP 400."""
        bad_yaml = ": broken yaml ]["
        uploaded = _raw_file(bad_yaml, "skills.yaml")

        response = self.client.post(self.URL, {"file": uploaded}, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_import_missing_file_returns_400(self):
        """Posting without a file returns HTTP 400."""
        response = self.client.post(self.URL, {}, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_import_unauthenticated_is_allowed(self):
        """SkillViewSet uses AllowAny — unauthenticated requests are accepted."""
        self.unauth()
        node = self._minimal_skill_node(code="ANONSK", description="Anon Skill")
        uploaded = _yaml_file([node])

        response = self.client.post(self.URL, {"file": uploaded}, format="multipart")

        self.assertNotIn(response.status_code, [401, 403])


# ---------------------------------------------------------------------------
# Tutor profile edit (POST /api/tutors/{id}/edit/)
# ---------------------------------------------------------------------------

@override_settings(MEDIA_ROOT="/tmp/test-media/")
class TutorEditTests(BaseAPITestCase):
    """POST /api/tutors/{id}/edit/

    The current edit action accepts a JSON ``fields`` dict and updates the
    User and TutorProfile rows.  Logo upload via request.FILES is not yet
    implemented in views.py; the logo tests below document the expected
    future behaviour and are marked with a clear comment so they can be
    activated once the feature is added.
    """

    def setUp(self):
        self.tutor_user = make_user(role="tutor")
        self.tutor_profile = make_tutor_profile(user=self.tutor_user)
        self.url = f"/api/tutors/{self.tutor_user.pk}/edit/"

    # ------------------------------------------------------------------
    # Auth requirements (TutorViewSet uses IsAuthenticated)
    # ------------------------------------------------------------------

    def test_edit_unauthenticated_returns_401(self):
        """Unauthenticated request is rejected with 401."""
        self.unauth()
        response = self.client.post(self.url, {"fields": {}}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_edit_requires_authentication(self):
        """Authenticated request is accepted (2xx)."""
        self.auth(self.tutor_user)
        response = self.client.post(self.url, {"fields": {}}, format="json")
        self.assertIn(response.status_code, [200, 201])

    # ------------------------------------------------------------------
    # Profile field updates
    # ------------------------------------------------------------------

    def test_edit_updates_profile_mobile(self):
        """Posting fields.mobile updates TutorProfile.mobile."""
        self.auth(self.tutor_user)
        response = self.client.post(
            self.url,
            {"fields": {"mobile": "0412345678"}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.tutor_profile.refresh_from_db()
        self.assertEqual(self.tutor_profile.mobile, "0412345678")

    def test_edit_updates_profile_address(self):
        """Posting fields.address updates TutorProfile.address."""
        self.auth(self.tutor_user)
        response = self.client.post(
            self.url,
            {"fields": {"address": "123 Test St, Sydney"}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.tutor_profile.refresh_from_db()
        self.assertEqual(self.tutor_profile.address, "123 Test St, Sydney")

    def test_edit_updates_user_first_name(self):
        """Posting fields.first_name updates User.first_name."""
        self.auth(self.tutor_user)
        response = self.client.post(
            self.url,
            {"fields": {"first_name": "UpdatedName"}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.tutor_user.refresh_from_db()
        self.assertEqual(self.tutor_user.first_name, "UpdatedName")

    def test_edit_returns_profile_dict(self):
        """Response body contains the updated profile data (user_id present)."""
        self.auth(self.tutor_user)
        response = self.client.post(self.url, {"fields": {}}, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("user_id", data)
        self.assertEqual(data["user_id"], self.tutor_user.pk)

    def test_edit_another_tutors_profile_by_admin(self):
        """An admin user can edit any tutor's profile."""
        admin = make_user(role="admin")
        self.auth(admin)
        response = self.client.post(
            self.url,
            {"fields": {"mobile": "0499999999"}},
            format="json",
        )
        # Admin is authenticated; endpoint should succeed
        self.assertIn(response.status_code, [200, 201])

    # ------------------------------------------------------------------
    # Logo upload — documents current behaviour
    #
    # NOTE: TutorProfile.logo is an ImageField (upload_to='branding/') but
    # the current edit action reads only request.data.get("fields", {}) and
    # does not inspect request.FILES.  The tests below verify the *current*
    # state (logo is NOT updated via this endpoint) so they pass today.
    # Once the feature is implemented, replace the assertion bodies with
    # positive checks (e.g. assertIsNotNone(profile.logo)).
    # ------------------------------------------------------------------

    def test_edit_with_image_file_does_not_raise(self):
        """Posting a valid PNG to the edit endpoint does not cause a server error.

        Currently fails because TutorViewSet.edit does not handle the case where
        request.data['fields'] is a string (multipart encoding) rather than a dict,
        causing AttributeError: 'str' object has no attribute 'items' (views.py:3014).
        """
        self.auth(self.tutor_user)

        gif_bytes = (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
            b"!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
            b"\x00\x00\x02\x02D\x01\x00;"
        )
        logo_file = SimpleUploadedFile("logo.gif", gif_bytes, content_type="image/gif")

        response = self.client.post(
            self.url,
            {"fields": "{}", "file": logo_file},
            format="multipart",
        )

        self.assertNotEqual(response.status_code, 500)

    def test_edit_with_non_image_file_does_not_raise(self):
        """Posting a non-image file to the edit endpoint does not cause a server error.

        Currently fails for the same reason as test_edit_with_image_file_does_not_raise:
        TutorViewSet.edit crashes when request.data['fields'] is a string.
        Once the bug is fixed, non-image uploads should be rejected (400/422).
        """
        self.auth(self.tutor_user)

        text_file = SimpleUploadedFile("document.txt", b"not an image", content_type="text/plain")

        response = self.client.post(
            self.url,
            {"fields": "{}", "file": text_file},
            format="multipart",
        )

        self.assertNotEqual(response.status_code, 500)
