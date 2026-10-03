import unittest
import numpy as np
from ai.runtime.sonar_geometry import SurveyGeometry,rectify,project_box,sensor_navigation,offset_position,geodesic


def profile(side='STARBOARD',**overrides):
    data=dict(version='xtf-flat-bottom-v1',source_log_sha256='a'*64,configuration_reference='SYNTHETIC TEST ONLY NOT A SURVEY APPROVAL',projection_authorized=True,navigation_datum='WGS84',nav_units_code=3,timestamp_timezone='UTC',position_reference='SENSOR',channels={0:dict(side=side,sample_order='NEAR_TO_FAR')},altitude_source_reference='Synthetic known altitude 3 m',altitude_scale=1,heading_source_reference='Synthetic north heading',pose_alignment_reference='Synthetic aligned pose',zero_heave_verified=True,ground_resolution_m=.5)
    return SurveyGeometry.model_validate(dict(data,**overrides))


def rows(side='STARBOARD'):
    return [dict(channel=0,channel_type_raw=2 if side=='STARBOARD' else 1,nav_units_code=3,timestamp_raw=f'2020-01-01T00:00:{i:02d}',heading_raw=0,pitch_raw=0,roll_raw=0,heave_raw=0,altitude_raw=3,slant_range_m=10,sensor_x_raw=0,sensor_y_raw=i/111000,ship_x_raw=0,ship_y_raw=i/111000,samples=np.arange(100,dtype=np.uint16)*500) for i in range(16)]


class GeometryTests(unittest.TestCase):
    def test_port_starboard_slant_mapping_and_dimensions(self):
        for side,sign in [('STARBOARD',1),('PORT',-1)]:
            gray,geometry=rectify(rows(side),profile(side));self.assertEqual(gray.shape,(16,19))
            result=project_box([0,2,4,6],geometry)
            self.assertEqual(result['physical_dimensions']['width_m'],2)
            self.assertGreater(result['physical_dimensions']['height_m'],3)
            self.assertGreater(sign*result['geographic']['longitude'],0)
            self.assertEqual(geometry['status'],'OPERATOR_CONFIGURED_NOT_FIELD_VALIDATED')
        self.assertGreater(gray[0,0],gray[0,-1])

    def test_far_to_near_preserves_pairing(self):
        a=rows();b=[dict(r,samples=r['samples'][::-1]) for r in a]
        p=profile();q=profile(channels={0:dict(side='STARBOARD',sample_order='FAR_TO_NEAR')})
        np.testing.assert_array_equal(rectify(a,p)[0],rectify(b,q)[0])

    def test_missing_or_unsafe_geometry_is_rejected(self):
        for changes in [dict(altitude_raw=11),dict(altitude_raw=0),dict(roll_raw=8),dict(heave_raw=.1),dict(nav_units_code=0),dict(timestamp_raw=None),dict(channel_type_raw=1),dict(sensor_y_raw=float('nan'))]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):sensor_navigation(dict(rows()[0],**changes),profile())
        with self.assertRaises(ValueError):profile(forward_offset_m=1)
        with self.assertRaises(ValueError):SurveyGeometry.model_validate({})
        bad=rows();bad[1]['timestamp_raw']=bad[0]['timestamp_raw']
        with self.assertRaises(ValueError):rectify(bad,profile())
        bad=rows();bad[1]['sensor_y_raw']=10
        with self.assertRaises(ValueError):rectify(bad,profile())

    def test_rotated_lever_arm_and_geodesic(self):
        p=profile(position_reference='VESSEL_GPS',forward_offset_m=.2,starboard_offset_m=1.85,down_offset_m=.75)
        row=rows()[0];result=sensor_navigation(row,p)
        self.assertAlmostEqual(geodesic().Inverse(0,0,result['latitude'],result['longitude'])['s12'],np.hypot(.2,1.85),places=5)
        result=sensor_navigation(dict(row,heading_raw=90),p)
        self.assertLess(result['latitude'],0);self.assertGreater(result['longitude'],0)
        lat,lon=offset_position(0,0,0,100)
        self.assertAlmostEqual(geodesic().Inverse(0,0,lat,lon)['s12'],100,places=6)

    def test_single_row_and_outside_box(self):
        _,g=rectify(rows()[:1],profile())
        self.assertIsNone(project_box([0,0,2,1],g)['physical_dimensions']['height_m'])
        self.assertEqual(project_box([0,0,2,1],g)['physical_dimensions']['height_status'],'UNAVAILABLE_SINGLE_PING')
        with self.assertRaises(ValueError):project_box([-1,0,2,1],g)

if __name__=='__main__':unittest.main()
