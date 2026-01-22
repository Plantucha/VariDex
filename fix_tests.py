#!/usr/bin/env python3
"""Fix the 2 failing tests in test_gnomad_integration.py"""

import re

# Read the test file
with open('tests/test_gnomad_integration.py', 'r') as f:
    content = f.read()

print("Fixing test_gnomad_integration.py...")

# Fix 1: test_get_variant_frequency_found
# The mock response needs proper nested structure with 'data' -> 'variant'
fix1_search = r'(def test_get_variant_frequency_found\(self, mock_post\):.*?""".*?""")'
fix1_replace = r'''\1
        mock_response = Mock()
        # Properly structure the mock response
        mock_response.json.return_value = {
            "data": {
                "variant": {
                    "variantId": "1-12345-A-G",
                    "genome": {
                        "ac": 10,
                        "an": 10000,
                        "af": 0.001,
                        "filters": ["PASS"],
                        "populations": []
                    },
                    "exome": None
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = GnomadClient(rate_limit=False)
        result = client.get_variant_frequency("1", 12345, "A", "G")

        assert result is not None
        assert result.genome_af == 0.001
        assert result.genome_ac == 10'''

# Apply fix 1 - find and replace the whole test function
pattern1 = r'def test_get_variant_frequency_found\(self, mock_post\):.*?(?=\n    def |\n\nclass |\Z)'
replacement1 = '''def test_get_variant_frequency_found(self, mock_post):
        """Test variant found in gnomAD."""
        mock_response = Mock()
        # Properly structure the mock response
        mock_response.json.return_value = {
            "data": {
                "variant": {
                    "variantId": "1-12345-A-G",
                    "genome": {
                        "ac": 10,
                        "an": 10000,
                        "af": 0.001,
                        "filters": ["PASS"],
                        "populations": []
                    },
                    "exome": None
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = GnomadClient(rate_limit=False)
        result = client.get_variant_frequency("1", 12345, "A", "G")

        assert result is not None
        assert result.genome_af == 0.001
        assert result.genome_ac == 10
'''

content = re.sub(pattern1, replacement1, content, flags=re.DOTALL)

# Fix 2: test_extract_coordinates_missing
# Add the missing 'position' parameter to VariantData
pattern2 = r'def test_extract_coordinates_missing\(self\):.*?(?=\n    def |\n\nclass |\Z)'
replacement2 = '''def test_extract_coordinates_missing(self):
        """Test coordinate extraction with missing fields."""
        # VariantData requires position parameter
        variant = VariantData(
            rsid="rs123",
            chromosome="1",
            position=12345,  # Required parameter
            genotype="A/G",
            ref_allele=None,  # Optional - missing
            alt_allele=None   # Optional - missing
        )

        classifier = ACMGClassifierV7(enable_gnomad=False)
        coords = classifier._extract_coordinates(variant)

        # Should handle missing ref/alt gracefully
        assert coords.get("chromosome") == "1"
        assert coords.get("position") == 12345
        assert coords.get("ref") is None
        assert coords.get("alt") is None
'''

content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)

# Write the fixed content
with open('tests/test_gnomad_integration.py', 'w') as f:
    f.write(content)

print("✅ Fixed test_get_variant_frequency_found - properly structured mock response")
print("✅ Fixed test_extract_coordinates_missing - added required 'position' parameter")
print("\nRun: pytest tests/test_gnomad_integration.py -v")
