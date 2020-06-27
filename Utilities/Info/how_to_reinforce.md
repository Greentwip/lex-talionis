In items.xml

```
    <item name="Reinforce">
        <id>so_Reinforce</id>
        <spritetype>Skills</spritetype>
        <spriteid>9,0</spriteid>
        <components>usable,booster,beneficial,call_item_script,exp</components>
        <weapontype>None</weapontype>

        <value>0</value>
        <RNG>0</RNG>
        <desc>Summons reinforcements</desc>
        <targets>Ally</targets>
        <LVL>--</LVL>
        <exp>13</exp>
    </item>
```

The item can be used by itself without an associated skill if you want

In your UnitLevel.txt
```
# Created units
other;2;w_Create;Soldier;Iron Lance;0,0;Pursue;Resistance
```

In Data/callItemScript.txt
Create one if one does not already exist
```
if;self.unit2.id == "so_Reinforce"
    set_origin
    create_unit;w_Create;self.unit.level;o1,0;warp;closest
    create_unit;w_Create;self.unit.level;o-1,0;warp;closest
    create_unit;w_Create;self.unit.level;o0,-1;warp;closest
    create_unit;w_Create;self.unit.level;o0,1;warp;closest
end
```

In status.xml
```
    <status name="Reinforce">
        <id>Reinforce</id>
        <image_index>9,0</image_index>
        <desc>Activated. Summons four new friends.</desc>
        <components>activated_item,class_skill</components>

        <activated_item>so_Reinforce</activated_item>
    </status>
```
