local addonName, ns = ...

-- Owned player marker: exact native floors or published reference-world bounds.
-- Outdoor coordinates and dungeon entrances never establish interior position.
ns.dungeonPlayerStatus = "Open a dungeon map to check live position."
local function number(value, maximum)
    return ns.Public(value) and type(value) == "number" and value == value and value >= 0 and value <= maximum
end
local function worldNumber(value)
    return ns.Public(value) and type(value) == "number" and value == value and math.abs(value) < 1000000
end
local function currentFloor(frame)
    local id = C_Map and ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    if ns.GuideInteger(id) and id > 0 then
        for floor, map in ipairs(frame.data and frame.data.maps or {}) do
            -- Only an exact native UI map can provide coordinates for its artwork.
            if not map.reference and map.mapID == id then return floor, id end
        end
    end
    -- Some Classic interiors retain the outdoor best-map ID. A confirmed
    -- instance with exactly one native floor is unambiguous; multi-floor maps
    -- still require the client's actual floor ID.
    local maps = frame.data and frame.data.maps or {}
    local key = ns.DungeonEntryKey()
    if key and frame.data and key == frame.data.key and #maps == 1 and not maps[1].reference
        and ns.GuideInteger(maps[1].mapID) then return 1, maps[1].mapID end
end
local function referencePosition(frame)
    local key, instance = ns.DungeonEntryKey()
    if not key or not frame.data or key ~= frame.data.key or not ns.GuideInteger(instance) or instance < 1 then
        return nil, nil, nil, nil, "Not inside this dungeon; reference player hidden."
    end
    local wx, wy, _, world = ns.ReadPublic(UnitPosition, "player")
    if not worldNumber(wx) or not worldNumber(wy) or not ns.GuideInteger(world) or world ~= instance then
        return nil, nil, nil, nil, "No public matching instance world position; reference map stays static."
    end
    local found, x, y
    for floor, map in ipairs(frame.data.maps or {}) do
        local b = map.reference and map.worldBounds
        if b and b.instanceMapID == instance and worldNumber(b.left) and worldNumber(b.right)
            and worldNumber(b.bottom) and worldNumber(b.top) and b.left ~= b.right and b.bottom ~= b.top then
            -- Same axis reversal as the compiler's static spawn projection.
            local px, py = (b.right - wy) / (b.right - b.left), (b.top - wx) / (b.top - b.bottom)
            if number(px, 1) and number(py, 1) then
                if found then return nil, nil, nil, nil, "Overlapping reference floors; player floor is unconfirmed." end
                found, x, y = floor, px, py
            end
        end
    end
    if found then return found, instance, x, y end
    return nil, nil, nil, nil, "World position outside mapped reference floors; player hidden."
end
local function coordinates(vector)
    if not ns.Public(vector) or type(vector) ~= "table" and type(vector) ~= "userdata" then return end
    local x, y = ns.ReadPublic(vector.GetXY, vector)
    if number(x, 1) and number(y, 1) and not (x == 0 and y == 0) then return x, y end
end
local function worldPosition(id)
    if not C_Map or type(CreateVector2D) ~= "function" or type(UnitPosition) ~= "function" then return end
    local wx, wy, _, instance = ns.ReadPublic(UnitPosition, "player")
    if not worldNumber(wx) or not worldNumber(wy)
        or not ns.GuideInteger(instance) then return end
    local continent = ns.ReadPublic(C_Map.GetWorldPosFromMapPos, id, CreateVector2D(0, 0))
    if continent ~= instance then return end
    local mapID, vector = ns.ReadPublic(C_Map.GetMapPosFromWorldPos, instance, CreateVector2D(wx, wy), id)
    if mapID ~= id then return end
    return coordinates(vector)
end
function ns.LocateDungeonPlayer(frame)
    frame = frame or ns.dungeonViewer
    if not frame then return false end
    local floor = currentFloor(frame)
    if not floor then floor = referencePosition(frame) end
    if not floor then return false end
    frame.floor, frame.followPlayer = floor, true
    return true
end

function ns.UpdateDungeonPlayer(frame)
    if not frame or not frame.playerMarker then return end
    local marker, geometry = frame.playerMarker, frame.playerGeometry
    marker:Hide()
    if frame.nativePlayer then frame.nativePlayer:Hide() end
    if not frame:IsShown() then return end
    local floor, id = currentFloor(frame)
    local x, y, reason, source
    if not floor then
        floor, id, x, y, reason = referencePosition(frame)
        source = "reference-world"
    end
    if frame.refresh and frame.playerLocatable ~= (floor ~= nil) then
        -- Keep the refresh action available, but do not offer a misleading
        -- Locate me label when Classic provides no usable interior position.
        frame.playerLocatable = floor ~= nil
        frame.refresh.caption:SetText(floor and "Locate me" or "Static map")
        ns.UIHelp(frame.refresh, floor and "Refresh the map and follow your current floor."
            or "Live player position is unavailable here. Click to check again.")
    end
    if not floor then ns.dungeonPlayerStatus = reason or "No matching player floor; map stays static."; return end
    if frame.followPlayer and floor ~= frame.floor and not frame.sizing and not frame.rendering and not frame.layingOut then
        frame.floor = floor
        ns.RenderDungeonViewer()
        return
    end
    if floor ~= frame.floor then ns.dungeonPlayerStatus = "Viewing another floor; click Locate me to return."; return end
    if not geometry or geometry.map ~= frame.data.maps[floor] then ns.dungeonPlayerStatus = "Map artwork unavailable; live marker hidden."; return end
    if not source then
        x, y = coordinates(C_Map and ns.ReadPublic(C_Map.GetPlayerMapPosition, id, "player"))
        source = "native"
        if not x then x, y = worldPosition(id); source = "world-to-map" end
    end
    if not x then
        if frame.nativePlayer and frame.nativePlayer.mapID == id and not frame.nativePlayerFailed then
            -- The native frame renders a unit directly. It does not return
            -- restricted coordinates to addon Lua or borrow reference geometry.
            frame.nativePlayer:Show()
            ns.dungeonPlayerStatus = "Native player renderer on floor " .. id .. "; Lua position unavailable."
        else ns.dungeonPlayerStatus = "No public position for native floor " .. id .. "; map stays static." end
        return
    end
    local facing = ns.ReadPublic(GetPlayerFacing)
    local directional = number(facing, math.pi * 2) and marker.hasArrow
    marker.arrow:SetShown(directional == true); marker.dot:SetShown(not directional)
    if directional then marker.arrow:SetRotation(facing) end
    marker:ClearAllPoints()
    marker:SetPoint("CENTER", frame.map, "TOPLEFT", geometry.x + x * geometry.width, -geometry.y - y * geometry.height)
    marker:Show()
    ns.dungeonPlayerStatus = "Live " .. source .. " position on floor " .. id .. (directional and " with facing." or "; facing unavailable.")
end

function ns.SetDungeonPlayerGeometry(frame, map, ox, oy, scale)
    frame.playerGeometry = map and (not map.reference and map.mapID or map.reference and map.worldBounds) and {
        map = map, mapID = not map.reference and map.mapID or nil,
        x = ox, y = oy, width = map.width * scale, height = map.height * scale} or nil
    if frame.playerGeometry and frame.playerGeometry.mapID then
        if not frame.nativePlayerTried then
            frame.nativePlayerTried = true
            local ok, renderer = pcall(CreateFrame, "UnitPositionFrame", nil, frame.map)
            if ok and renderer and type(renderer.SetUiMapID) == "function" and type(renderer.AddUnit) == "function"
                and type(renderer.FinalizeUnits) == "function" and type(renderer.ClearUnits) == "function" then
                frame.nativePlayer = renderer
                renderer:Hide(); renderer:EnableMouse(false); renderer:SetFrameLevel(frame.map:GetFrameLevel() + 30)
            end
        end
        local renderer, geometry = frame.nativePlayer, frame.playerGeometry
        if renderer and not frame.nativePlayerFailed then
            renderer:Hide(); renderer:ClearAllPoints()
            renderer:SetPoint("TOPLEFT", frame.map, "TOPLEFT", geometry.x, -geometry.y)
            renderer:SetSize(geometry.width, geometry.height)
            -- No Blizzard Lua mixin, native-map frame, aura reader or tooltip
            -- hook is involved. These are documented methods of our own frame.
            local ok = pcall(function()
                renderer:SetUiMapID(geometry.mapID); renderer:ClearUnits()
                renderer:AddUnit("player", "Interface\\Minimap\\MinimapArrow", 26, 26, 1, 1, 1, 1, 7, true)
                renderer:FinalizeUnits()
            end)
            if ok then renderer.mapID = geometry.mapID else frame.nativePlayerFailed = true; renderer:Hide() end
        end
    elseif frame.nativePlayer then frame.nativePlayer:Hide() end
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

function ns.DungeonPlayerDiagnostics(output, frame)
    if not frame or not frame:IsShown() then return end
    local key, instance = ns.DungeonEntryKey()
    local wx, wy, _, world = ns.ReadPublic(UnitPosition, "player")
    local xy = worldNumber(wx) and worldNumber(wy) and string.format("%.2f, %.2f", wx, wy) or "unavailable/restricted"
    local map = frame.data and frame.data.maps[frame.floor]
    local b = map and map.worldBounds
    output("Dungeon world position: matching instance " .. (key == (frame.data and frame.data.key) and "yes" or "no")
        .. "; instance " .. (ns.GuideInteger(instance) and instance or "unknown")
        .. "; UnitPosition map " .. (ns.GuideInteger(world) and world or "unknown") .. "; XY " .. xy
        .. "; reference rectangle " .. (b and b.sourceTable .. " " .. b.sourceID or "unavailable") .. ".")
end
