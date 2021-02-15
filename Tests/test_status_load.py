# Test image loading
import os
import pstats
import cProfile

import Code.GlobalConstants as GC
import Code.StatusObject as StatusObject

def main():
    all_statuses = []
    for status in GC.STATUSDATA.getroot().findall('status'):
        s_id = status.find('id').text
        print(s_id)
        all_statuses.append(StatusObject.statusparser(s_id))
    assert len(all_statuses) > 0

if __name__ == '__main__':
    cProfile.run("main()", "Profile.prof")
    s = pstats.Stats("Profile.prof")
    s.strip_dirs().sort_stats("time").print_stats(10)
    os.remove("Profile.prof")
