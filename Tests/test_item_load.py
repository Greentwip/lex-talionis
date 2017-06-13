# Test image loading
import os
import pstats
import cProfile

#pygame.display.set_mode((600, 400))
import Code.GlobalConstants as GC
import Code.ItemMethods as ItemMethods

def main():
    ITEMDATA = GC.create_item_dict()
    items = []
    for item in ITEMDATA:
        print(item)
        items.append(ItemMethods.itemparser(item))
    assert len(items) > 0

if __name__ == '__main__':
    cProfile.run("main()", "Profile.prof")
    s = pstats.Stats("Profile.prof")
    s.strip_dirs().sort_stats("time").print_stats(10)
    os.remove("Profile.prof")