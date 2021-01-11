import unittest
import pandas as pd

from transformscripts import change_method_name_metrics, ctor_to_class_name, change_method_name_commits, \
    change_method_name_usage, change_name_coverage, remove_generics


class MyTestCase(unittest.TestCase):

    expected_output = [
        "ShareX.HelpersLib.OctreeQuantizer.Octree.Octree(Int32)",
        "ShareX.HelpersLib.Reflector.New(String,Object[])",
        "ShareX.HelpersLib.MyListView.WndProc(Message)",
        "ShareX.HelpersLib.GrayscaleQuantizer.QuantizePixel(Color32)",
        "ShareX.HelpersLib.CMYK.CMYK(Int32,Int32,Int32,Int32,Int32)",
        "Application.Workspace.WorkspaceAppService.DeleteCitation(CitationInput)",
        "Seed.Host.DefaultSettingsCreator.AddSettingIfNotExists(String,String,Nullable<Int32>)",
        "DataAccess.Queries.QueryStore.Format(String,String[])"
    ]

    def test_source_code_metrics_report_transformation(self):
        d = {'Method': ["ShareX.HelpersLib.OctreeQuantizer+Octree..ctor(Int32)",
                        "ShareX.HelpersLib.Reflector.New(String,Object[])",
                        "ShareX.HelpersLib.MyListView.WndProc(Message&)",
                        "ShareX.HelpersLib.GrayscaleQuantizer.QuantizePixel(Quantizer+Color32)",
                        "ShareX.HelpersLib.CMYK..ctor(Int32,Int32,Int32,Int32,Int32)",
                        "Application.Workspace.WorkspaceAppService.DeleteCitation(CitationInput)",
                        "Seed.Host.DefaultSettingsCreator.AddSettingIfNotExists(String,String,Nullable<Int32>)"]}
        df = pd.DataFrame(data=d)
        df['Method'] = df['Method'].apply(change_method_name_metrics)
        df['Method'] = df['Method'].apply(ctor_to_class_name)

        self.assertEqual(self.expected_output[0], df['Method'][0])
        self.assertEqual(self.expected_output[1], df['Method'][1])
        self.assertEqual(self.expected_output[2], df['Method'][2])
        self.assertEqual(self.expected_output[3], df['Method'][3])
        self.assertEqual(self.expected_output[4], df['Method'][4])
        self.assertEqual(self.expected_output[5], df['Method'][5])
        self.assertEqual(self.expected_output[6], df['Method'][6])

    def test_change_metrics_report_transformation(self):
        d = {'Method': ["ShareX.HelpersLib::OctreeQuantizer::Octree::Octree( int maxColorBits)",
                        "ShareX.HelpersLib::Reflector::New( string name , params object [ ] parameters)",
                        "ShareX.HelpersLib::MyListView::WndProc( ref Message msg)",
                        "ShareX.HelpersLib::GrayscaleQuantizer::QuantizePixel( Color32 pixel)",
                        "ShareX.HelpersLib::CMYK::CMYK( int cyan , int magenta , int yellow , int key , int alpha = 255)",
                        "Application.Workspace::WorkspaceAppService::DeleteCitation( [ FromBody ] CitationInput citation)",
                        "Seed.Host::DefaultSettingsCreator::AddSettingIfNotExists( string name , string value , int ? tenantId = null)"]}
        df = pd.DataFrame(data=d)
        df['Method'] = df['Method'].apply(change_method_name_commits)

        self.assertEqual(self.expected_output[0], df['Method'][0])
        self.assertEqual(self.expected_output[1], df['Method'][1])
        self.assertEqual(self.expected_output[2], df['Method'][2])
        self.assertEqual(self.expected_output[3], df['Method'][3])
        self.assertEqual(self.expected_output[4], df['Method'][4])
        self.assertEqual(self.expected_output[5], df['Method'][5])
        self.assertEqual(self.expected_output[6], df['Method'][6])

    def test_usage_metrics_report_transformation(self):
        d = {'Method': ["ShareX.HelpersLib.Reflector.New(String, params Object[])",
                        "ShareX.HelpersLib.MyListView.WndProc(ref Message)",
                        "ShareX.HelpersLib.CMYK..ctor(Int32, Int32, Int32, Int32, Int32)",
                        "Application.Workspace.WorkspaceAppService.DeleteCitation(CitationInput)",
                        "Seed.Host.DefaultSettingsCreator.AddSettingIfNotExists(String,String,Nullable)"]}
        df = pd.DataFrame(data=d)
        df['Method'] = df['Method'].apply(change_method_name_usage)
        df['Method'] = df['Method'].apply(ctor_to_class_name)

        self.assertEqual(self.expected_output[1], df['Method'][0])
        self.assertEqual(self.expected_output[2], df['Method'][1])
        self.assertEqual(self.expected_output[4], df['Method'][2])
        self.assertEqual(self.expected_output[5], df['Method'][3])
        self.assertEqual("Seed.Host.DefaultSettingsCreator.AddSettingIfNotExists(String,String,Nullable)", df['Method'][4])

    def test_test_coverage_report_transformation(self):
        d = {'Method': ["Application.Workspace.WorkspaceAppService.DeleteCitation(CitationInput)",
                        "Seed.Host.DefaultSettingsCreator.AddSettingIfNotExists(string,string,Nullable<int>)",
                        "DataAccess.Queries.QueryStore.Format(string,params string[])"]}
        df = pd.DataFrame(data=d)
        df['Method'] = df['Method'].apply(change_name_coverage)

        self.assertEqual(self.expected_output[5], df['Method'][0])
        self.assertEqual(self.expected_output[6], df['Method'][1])
        self.assertEqual(self.expected_output[7], df['Method'][2])

    def test_generics_removal_transformation(self):
        d = {'Generics': ["abc(String,String,Nullable<Int32>)",
                          "abc(Nullable<Int32>,String,String)",
                          "abc(Nullable<Int32>)",
                          "abc(Nullable<Int32,Int32>)",
                          "abc(List<Nullable<Int32>>)",
                          "abc(List<Nullable<Int32,Int32>>)",
                          "abc(List<Nullable<Int32,Int32>>,String<Boolean>)"]}

        df = pd.DataFrame(data=d)
        df['Generics'] = df['Generics'].apply(remove_generics)

        self.assertEqual("abc(String,String,Nullable)", df['Generics'][0])
        self.assertEqual("abc(Nullable,String,String)", df['Generics'][1])
        self.assertEqual("abc(Nullable)", df['Generics'][2])
        self.assertEqual("abc(Nullable)", df['Generics'][3])
        self.assertEqual("abc(List)", df['Generics'][4])
        self.assertEqual("abc(List)", df['Generics'][5])
        self.assertEqual("abc(List,String)", df['Generics'][6])


if __name__ == '__main__':
    unittest.main()
