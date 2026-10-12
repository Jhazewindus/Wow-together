local addonName, ns = ...

local titles = {
    ["wailing-caverns"] = "Wailing Caverns Approach",
    ["deadmines"] = "Deadmines Approach",
    ["blackfathom-deeps"] = "Blackfathom Deeps Approach",
    ["gnomeregan"] = "Gnomeregan Approach",
    ["scarlet-monastery"] = "Scarlet Monastery Approach",
    ["uldaman"] = "Uldaman Approach",
    ["razorfen-downs"] = "Razorfen Downs Approach",
}
local sourceDungeon = {
    ["wailing-caverns"] = "wailing-caverns", deadmines = "the-deadmines",
    ["blackfathom-deeps"] = "blackfathom-deeps", gnomeregan = "gnomeregan",
    ["scarlet-monastery"] = "scarlet-monastery", uldaman = "uldaman",
    ["razorfen-downs"] = "razorfen-downs",
}
local function valid(v, limit)
    return ns.Public(v) and type(v) == "number" and v == v and math.abs(v) < (limit or 1000000)
end
local function pointXY(value)
    if not ns.Public(value) or type(value) ~= "table" and type(value) ~= "userdata" then return end
    local x, y = ns.ReadPublic(value.GetXY, value)
    if valid(x) and valid(y) then return x, y end
end
local function worldPoint(mapID, x, y)
    if not C_Map or type(CreateVector2D) ~= "function" then return end
    local continent, point = ns.ReadPublic(C_Map.GetWorldPosFromMapPos, mapID, CreateVector2D(x, y))
    local wx, wy = pointXY(point)
    if ns.GuideInteger(continent) and wx and wy then return continent, wx, wy end
end
local function currentWorld()
    if not C_Map then return end
    local mapID = ns.ReadPublic(C_Map.GetBestMapForUnit, "player")
    if not ns.GuideInteger(mapID) or mapID <= 0 then return end
    local point = ns.ReadPublic(C_Map.GetPlayerMapPosition, mapID, "player")
    local x, y = pointXY(point)
    if not x or not y or x == 0 and y == 0 then return end
    local continent, wx, wy = worldPoint(mapID, x, y)
    if continent then return mapID, continent, wx, wy end
end

local function prepare(model)
    if model.ready then return model end
    local minX, maxX, minY, maxY = math.huge, -math.huge, math.huge, -math.huge
    local groups, tiles = model.groups or {}, {}
    for _, tile in ipairs(model.tiles or {}) do
        local group = groups[tile[2] + 1]
        if group then
            -- Blizzard's WMO minimap grid uses 128 model units per 256 px block.
            local x = group.min[1] * 2 + tile[3] * 256
            local y = group.min[2] * 2 + tile[4] * 256
            local item = {id = tile[1], x = x, y = y, width = tile[5], height = tile[6],
                depth = group.min[3], key = model.key}
            tiles[#tiles + 1] = item
            minX, maxX = math.min(minX, x), math.max(maxX, x + item.width)
            minY, maxY = math.min(minY, y), math.max(maxY, y + item.height)
        end
    end
    table.sort(tiles, function(a, b) return a.depth < b.depth end)
    model.bounds = {left = minX, right = maxX, bottom = minY, top = maxY}
    model.renderTiles, model.ready = tiles, minX < maxX and minY < maxY
    return model
end

function ns.HasDungeonApproach(key)
    for _, model in ipairs(ns.approachMapData.models) do if model.dungeonKey == key then return true end end
    return false
end

local function wmoPixel(model, wx, wy)
    local p, half = model.placement, ns.approachMapData.worldHalf
    local dx, dy = wx - (half - p.z), wy - (half - p.x)
    local angle = math.rad(p.yaw - 180)
    local c, s = math.cos(angle), math.sin(angle)
    local localX, localY = (c * dx + s * dy) / p.scale, (-s * dx + c * dy) / p.scale
    local b = model.bounds
    -- Group bounds are doubled into client-map pixels in prepare(); apply the
    -- same conversion to the player's model-space point before subtracting.
    return localX * 2 - b.left, b.top - localY * 2
end

local function terrainPixel(model, wx, wy)
    local t = model.terrain
    local tx = (t.worldOrigin - wy) / t.tileWorldSize
    local ty = (t.worldOrigin - wx) / t.tileWorldSize
    local x = (tx - t.originX) * t.tilePixels
    local y = (t.originY + 2 - ty) * t.tilePixels
    return x, y
end

local function position(model, wx, wy)
    if model.terrain then return terrainPixel(model, wx, wy) end
    return wmoPixel(model, wx, wy)
end

local function inside(model, x, y)
    if not valid(x) or not valid(y) then return false end
    if model.terrain then return x >= 0 and x <= model.terrain.width and y >= 0 and y <= model.terrain.height end
    local b = model.bounds
    return b and x >= 0 and x <= b.right - b.left and y >= 0 and y <= b.top - b.bottom
end

local function findEntrance(model)
    local dungeon = ns.dungeonData and ns.dungeonData.dungeons and ns.dungeonData.dungeons[model.dungeonKey]
    for _, entry in ipairs(dungeon and dungeon.entrances or {}) do
        if entry.published == true and valid(entry.x, 1) and valid(entry.y, 1) then
            local continent, wx, wy = worldPoint(entry.mapID, entry.x, entry.y)
            if continent == model.continent and wx and wy then
                local x, y = position(model, wx, wy)
                if inside(model, x, y) then return x, y, entry.name end
            end
        end
    end
end

local function create()
    if ns.approachMap then return ns.approachMap end
    local frame = CreateFrame("Frame", "WowTogetherApproachMap", UIParent, "BackdropTemplate")
    ns.approachMap = frame
    frame:SetSize(520, 440); frame:SetPoint("BOTTOMLEFT", UIParent, "BOTTOMLEFT", 28, 180)
    frame:SetFrameStrata("DIALOG"); frame:SetClampedToScreen(true); frame:SetMovable(true); frame:EnableMouse(true)
    frame:RegisterForDrag("LeftButton"); frame:SetScript("OnDragStart", frame.StartMoving)
    frame:SetScript("OnDragStop", function(self) self:StopMovingOrSizing() end)
    ns.UIPanel(frame)
    frame.title = ns.UILabel(frame, "GameFontNormalLarge", 17); frame.title:SetPoint("TOPLEFT", 14, -12); frame.title:SetSize(420, 24)
    frame.status = ns.UILabel(frame, nil, 10); frame.status:SetPoint("TOPLEFT", 16, -40); frame.status:SetSize(470, 18)
    frame.map = CreateFrame("Frame", nil, frame, "BackdropTemplate"); ns.UIPanel(frame.map)
    frame.map:SetClipsChildren(true)
    frame.close = ns.UIClose(frame)
    frame.journal = ns.UIButton(frame, "Dungeon journal", 118, function()
        local key = frame.model and frame.model.dungeonKey
        if key then frame.transition = true; frame:Hide(); ns.ShowDungeonViewer(key, true); frame.transition = nil end
    end)
    frame.journal:SetPoint("BOTTOMLEFT", 12, 10)
    frame.marker = CreateFrame("Frame", nil, frame.map); frame.marker:SetSize(24, 24)
    frame.marker.icon = frame.marker:CreateTexture(nil, "OVERLAY"); frame.marker.icon:SetAllPoints()
    frame.marker.icon:SetTexture("Interface\\Minimap\\MinimapArrow")
    frame.entrance = CreateFrame("Frame", nil, frame.map); frame.entrance:SetSize(22, 22)
    frame.entrance.icon = frame.entrance:CreateTexture(nil, "OVERLAY"); frame.entrance.icon:SetAllPoints()
    frame.entrance.icon:SetTexture("Interface\\TargetingFrame\\UI-RaidTargetingIcon_1")
    frame.entrance.label = ns.UILabel(frame.map, nil, 10); frame.entrance.label:SetText("Dungeon entrance")
    frame.entrance.label:SetTextColor(.98, .78, .25, 1); frame.entrance.label:SetSize(110, 16)
    frame.tiles = {}
    frame:SetScript("OnHide", function(self)
        if self.model and not self.transition then self.dismissed = self.model.key end
    end)
    ns.EnableWindowResize(frame, {key = "approachMap", minWidth = 360, minHeight = 300,
        maxWidth = 1100, maxHeight = 850, layout = function(self)
            local width, height = self:GetWidth(), self:GetHeight()
            self.title:SetWidth(width - 74); self.status:SetWidth(width - 32)
            self.map:ClearAllPoints(); self.map:SetPoint("TOPLEFT", 10, -64)
            self.map:SetSize(width - 20, height - 104)
            if self.model then ns.DrawApproachMap(self) end
        end})
    frame:Hide()
    return frame
end

function ns.DrawApproachMap(frame)
    frame = frame or ns.approachMap
    local model = frame and frame.model
    if not model then return end
    local map = frame.map
    for _, texture in ipairs(frame.tiles) do texture:Hide() end
    local width, height = map:GetWidth(), map:GetHeight()
    local dataWidth, dataHeight = model.terrain and model.terrain.width or model.bounds.right - model.bounds.left,
        model.terrain and model.terrain.height or model.bounds.top - model.bounds.bottom
    if width <= 0 or height <= 0 or dataWidth <= 0 or dataHeight <= 0 then return end
    local scale = math.min(width / dataWidth, height / dataHeight)
    local ox, oy = (width - dataWidth * scale) / 2, (height - dataHeight * scale) / 2
    frame.mapGeometry = {scale = scale, x = ox, y = oy, width = dataWidth, height = dataHeight}
    local sourceTiles = model.terrain and model.terrain.tiles or model.renderTiles
    for index, item in ipairs(sourceTiles or {}) do
        local texture = frame.tiles[index]
        if not texture then texture = map:CreateTexture(nil, "ARTWORK"); frame.tiles[index] = texture end
        local x, y, tw, th, fileID
        if model.terrain then
            fileID, tw, th = item[1], 512, 512
            x, y = item[2] * 512, item[3] * 512
        else
            fileID, tw, th = item.id, item.width, item.height
            x, y = item.x - model.bounds.left, model.bounds.top - item.y - th
        end
        texture:ClearAllPoints(); texture:SetPoint("TOPLEFT", ox + x * scale, -(oy + y * scale))
        texture:SetSize(tw * scale, th * scale)
        local okay = ns.ReadPublic(texture.SetTexture, texture, fileID)
        texture:SetShown(okay ~= false)
    end
    local ex, ey, entranceName = findEntrance(model)
    if ex and ey then
        frame.entrance:ClearAllPoints(); frame.entrance:SetPoint("CENTER", map, "TOPLEFT", ox + ex * scale, -(oy + ey * scale))
        frame.entrance:Show(); frame.entrance.label:ClearAllPoints()
        frame.entrance.label:SetPoint("LEFT", frame.entrance, "RIGHT", 2, 0); frame.entrance.label:SetText(entranceName or "Dungeon entrance")
        frame.entrance.label:Show()
    else frame.entrance:Hide(); frame.entrance.label:Hide() end
    frame.marker:Hide()
    frame.status:SetText(ex and "Gold star: dungeon entrance • Arrow: you" or "Arrow: you • Entrance location unavailable")
end

function ns.ShowDungeonApproach(key)
    if not ns.Option("approachMaps") then return false end
    for _, model in ipairs(ns.approachMapData.models) do
        if model.dungeonKey == key then
            prepare(model)
            local frame = create(); frame.model = model; frame.dismissed = nil; frame.autoOpened = false
            frame.title:SetText(titles[model.key] or "Dungeon approach")
            frame:Show(); frame:Raise(); ns.DrawApproachMap(frame)
            return true
        end
    end
    return false
end

local lastMap
function ns.CheckApproachMap()
    if not ns.db or not ns.Option("approachMaps") then
        if ns.approachMap then
            if ns.approachMap:IsShown() then ns.approachMap:Hide() end
            ns.approachMap.dismissed, ns.approachMap.autoOpened = nil, false
        end
        lastMap = nil
        return
    end
    local frame = ns.approachMap
    local entry = ns.DungeonEntryKey and ns.DungeonEntryKey()
    if entry then
        if frame and frame:IsShown() and frame.model then
            if frame.model.dungeonKey == entry then
                frame.transition = true; frame:Hide(); ns.ShowDungeonViewer(entry, true); frame.transition = nil
            elseif frame.autoOpened then
                frame.transition = true; frame:Hide(); frame.transition = nil
            end
        end
        lastMap = nil
        return
    end
    local mapID, continent, wx, wy = currentWorld()
    if not continent then
        if frame and frame.autoOpened and frame:IsShown() then frame.transition = true; frame:Hide(); frame.transition = nil end
        lastMap = nil
        return
    end
    local mapInfo = C_Map and ns.ReadPublic(C_Map.GetMapInfo, mapID)
    local parentMapID = type(mapInfo) == "table" and ns.Public(mapInfo.parentMapID) and mapInfo.parentMapID
    local match, mx, my
    local smallest = math.huge
    for _, model in ipairs(ns.approachMapData.models) do
        if continent == model.continent and (model.terrain or mapID == model.mapID or parentMapID == model.mapID) then
            prepare(model)
            local x, y = position(model, wx, wy)
            if model.ready and inside(model, x, y) then
                local size = model.terrain and model.terrain.width * model.terrain.height
                    or (model.bounds.right - model.bounds.left) * (model.bounds.top - model.bounds.bottom)
                if size < smallest then match, mx, my, smallest = model, x, y, size end
            end
        end
    end
    if not match then
        if frame and frame.model and frame.autoOpened and frame:IsShown() then frame.transition = true; frame:Hide(); frame.transition = nil end
        lastMap = nil
        if frame then frame.dismissed = nil end
        return
    end
    frame = create()
    if frame.dismissed == match.key then lastMap = match.key; return end
    if not frame:IsShown() then
        frame.model, frame.autoOpened = match, true
        frame.title:SetText(titles[match.key] or "Dungeon approach")
        frame:Show(); frame:Raise()
        ns.DrawApproachMap(frame)
        lastMap = match.key
    elseif frame.model ~= match then
        frame.model, frame.autoOpened = match, true
        frame.title:SetText(titles[match.key] or "Dungeon approach")
        ns.DrawApproachMap(frame); lastMap = match.key
    end
    local geometry = frame.mapGeometry
    if geometry and inside(match, mx, my) then
        frame.marker:ClearAllPoints()
        frame.marker:SetPoint("CENTER", frame.map, "TOPLEFT", geometry.x + mx * geometry.scale, -(geometry.y + my * geometry.scale))
        local facing = ns.ReadPublic(GetPlayerFacing)
        if valid(facing, math.pi * 2) then ns.ReadPublic(frame.marker.icon.SetRotation, frame.marker.icon, facing) end
        frame.marker:Show()
        frame.status:SetText("Live position • Walk to the gold entrance marker")
    else frame.marker:Hide() end
end

function ns.InitializeApproachMaps()
    create()
    local poll = CreateFrame("Frame")
    local elapsed = 0
    poll:SetScript("OnUpdate", function(_, delta)
        elapsed = elapsed + delta
        if elapsed < .5 then return end
        elapsed = 0
        ns.CheckApproachMap()
    end)
end

function ns.ApproachMapDiagnostics(output)
    output("Dungeon approach maps: seven Blizzard client maps; live position is outdoors only.")
end
