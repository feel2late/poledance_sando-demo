import datetime

def check_sub_for_intersections(sub_1_start_date, sub_1_end_date, sub_2_start_date, sub_2_end_date):
    return sub_1_start_date <= sub_2_end_date and sub_1_end_date >= sub_2_start_date

