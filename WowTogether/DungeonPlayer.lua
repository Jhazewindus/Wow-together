local addonName, ns = ...

-- Independent native-map adapter. A reference image or entrance location never
-- establishes the player's dungeon coordinates. HiddenMaps' public description
-- likewise limits its live tracking to supported pre-instance areas.
ns.dungeonPlayerStatus = "Open a dungeon map to check live position."
local function number(value, maximum)
    return ns.Public(value) and type(value) == "number" and value == value and value >= 0 and value <= maximum
end
local function currentFloor(frame)
    local id = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    if not ns.GuideInteger(id) or id < 1 then return end
    for floor, map in ipairs(frame.data and frame.data.maps or {}) do
        -- Only an exact native UI map can provide coordinates for its artwork.
        if not map.reference and map.mapID == id then return floor, id end
    end
end
function ns.LocateDungeonPlayer(frame)
    frame = frame or ns.dungeonViewer
    if not frame then return false end
    local floor = currentFloor(frame)
    if not floor then return false end
    frame.floor, frame.followPlayer = floor, true
    return true
end

function ns.UpdateDungeonPlayer(frame)
    if not frame or not frame.playerMarker then return end
    local marker, geometry = frame.playerMarker, frame.playerGeometry
    marker:Hide()
    if not frame:IsShown() then return end
    local floor, id = currentFloor(frame)
    if not floor then ns.dungeonPlayerStatus = "No matching native player floor; map stays static."; return end
    if frame.followPlayer and floor ~= frame.floor and not frame.sizing and not frame.rendering and not frame.layingOut then
        frame.floor = floor
        ns.RenderDungeonViewer()
        return
    end
    if floor ~= frame.floor then ns.dungeonPlayerStatus = "Viewing another floor; click Locate me to return."; return end
    if not geometry or geometry.mapID ~= id then ns.dungeonPlayerStatus = "Map artwork unavailable; live marker hidden."; return end
    local vector = C_Map and ns.ReadPublic(C_Map.GetPlayerMapPosition, id, "player")
    if not ns.Public(vector) or type(vector) ~= "table" and type(vector) ~= "userdata" then
        ns.dungeonPlayerStatus = "Client returned no public player position for this floor."; return
    end
    local x, y = ns.ReadPublic(vector.GetXY, vector)
    if not number(x, 1) or not number(y, 1) or x == 0 and y == 0 then
        ns.dungeonPlayerStatus = "Player position missing, restricted or outside this floor."; return
    end
    local facing = ns.ReadPublic(GetPlayerFacing)
    local directional = number(facing, math.pi * 2) and marker.hasArrow
    marker.arrow:SetShown(directional == true); marker.dot:SetShown(not directional)
    if directional then marker.arrow:SetRotation(facing) end
    marker:ClearAllPoints()
    marker:SetPoint("CENTER", frame.map, "TOPLEFT", geometry.x + x * geometry.width, -geometry.y - y * geometry.height)
    marker:Show()
    ns.dungeonPlayerStatus = directional and "Live native player position and facing." or "Live native position; facing unavailable."
end

function ns.SetDungeonPlayerGeometry(frame, map, ox, oy, scale)
    frame.playerGeometry = map and not map.reference and map.mapID and {
        mapID = map.mapID, x = ox, y = oy, width = map.width * scale, height = map.height * scale} or nil
    ns.UpdateDungeonPlayer(frame)
end

function ns.CreateDungeonPlayer(frame)
    local marker = CreateFrame("Frame", nil, frame.map)
    frame.playerMarker = marker
    marker:SetSize(26, 26); marker:SetFrameLevel(frame.map:GetFrameLevel() + 30)
    marker:EnableMouse(false)
    marker.arrow = marker:CreateTexture(nil, "OVERLAY"); marker.arrow:SetAllPoints()
    marker.hasArrow = ns.ReadPublic(marker.arrow.SetTexture, marker.arrow, "Interface\\Minimap\\MinimapArrow") == true
    marker.dot = ns.UILabel(marker, nil, 22, {0.3, 0.85, 1, 1})
    marker.dot:SetPoint("CENTER"); marker.dot:SetText("•"); marker.dot:SetJustifyH("CENTER")
    marker:Hide()
    -- Owned frame only: no hooks into Blizzard map, minimap, nameplates or
    -- Edit Mode. Repaint the marker at 10 Hz, not bosses/loot/quest lists.
    frame.map:SetScript("OnUpdate", function(_, elapsed)
        if not ns.Public(elapsed) or type(elapsed) ~= "number" then return end
        frame.playerElapsed = (frame.playerElapsed or 0) + elapsed
        if frame.playerElapsed >= .1 then frame.playerElapsed = 0; ns.UpdateDungeonPlayer(frame) end
    end)
end
