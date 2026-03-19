import unittest
import os
import subprocess
import shutil

class TestFBXTools(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Prepares the test environment."""
        cls.test_input_dir = "input"
        cls.test_output_dir = "test_output"
        cls.sample_file = "01-09-FBX.fbx"
        cls.script_path = "fbxtools.py"
        
        # Ensure the sample file exists before running tests
        if not os.path.exists(os.path.join(cls.test_input_dir, cls.sample_file)):
            raise FileNotFoundError(f"Missing sample file: {cls.sample_file} in {cls.test_input_dir}")

        # Clean up any previous test output
        if os.path.exists(cls.test_output_dir):
            shutil.rmtree(cls.test_output_dir)

    def run_tool(self, extra_args=[]):
        """Helper to run the fbxtools script with arguments. Uses --limit 1 for speed."""
        cmd = ["python", self.script_path, "-i", self.test_input_dir, "-o", self.test_output_dir, "--limit", "1"] + extra_args
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result

    def test_help_command(self):
        """Verify the --help flag works and provides guidance."""
        result = subprocess.run(["python", self.script_path, "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("FBX Tools", result.stdout)
        self.assertIn("--add-root", result.stdout)

    def test_basic_processing(self):
        """Verify basic mesh stripping and animation splitting."""
        result = self.run_tool()
        self.assertEqual(result.returncode, 0)
        
        # Check if output directory was created
        self.assertTrue(os.path.exists(self.test_output_dir))
        
        # Verify that at least one file was generated (splitting logic)
        outputs = [f for f in os.listdir(self.test_output_dir) if f.endswith(".fbx")]
        self.assertGreater(len(outputs), 0, "No output FBX files were generated.")
        
        # Check that the output contains the original filename prefix
        base_name = os.path.splitext(self.sample_file)[0]
        self.assertTrue(outputs[0].startswith(base_name), f"Output filename {outputs[0]} doesn't match expected prefix.")

    def test_add_root_feature(self):
        """Verify the --add-root flag runs without errors."""
        result = self.run_tool(["--add-root"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Successfully injected 'root' bone", result.stdout)

    def test_rescale_feature(self):
        """Verify the --rescale flag runs without errors."""
        result = self.run_tool(["--rescale", "0.01"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Rescaled by factor of 0.01", result.stdout)

    def test_rename_feature(self):
        """Verify the renaming logic runs without errors."""
        result = self.run_tool(["--rename-find", "Hips", "--rename-replace", "Pelvis"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Renamed 'Hips' to 'Pelvis'", result.stdout)

    def tearDown(self):
        """Clean up generated files after each test."""
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)

if __name__ == "__main__":
    unittest.main()
