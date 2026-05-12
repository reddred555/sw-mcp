"""
STUKACH MFG MCP Server
SolidWorks 2022 + ArtCAM 2012
Pipeline: модель → DXF/STL/3MF → G-code → WDMAX
"""
from fastmcp import FastMCP
import win32com.client
import pythoncom
import subprocess
import os

mcp = FastMCP("stukach-sw-mcp")

ARTCAM_EXE = r"C:\Program Files\ArtCAM 2012\ArtCAM.exe"
ARTCAM_MACROS = r"C:\STUKACH\sw-mcp\artcam_macros"
WORK_DIR = r"C:\STUKACH\work"

def _sw():
    """Get SolidWorks application from the current thread (safe for FastMCP threading)."""
    pythoncom.CoInitialize()
    return win32com.client.Dispatch("SldWorks.Application")

def _doc():
    doc = _sw().ActiveDoc
    if doc is None:
        raise RuntimeError("Немає активного документа. Відкрийте або створіть деталь.")
    return doc

# ─────────────────────────────────────────
# SOLIDWORKS — З'ЄДНАННЯ
# ─────────────────────────────────────────

@mcp.tool()
def sw_connect() -> str:
    """Підключитись до запущеного SolidWorks."""
    app = _sw()
    app.Visible = True
    return f"SolidWorks підключено. Версія: {app.RevisionNumber}"

@mcp.tool()
def sw_list_documents() -> str:
    """Показати всі відкриті документи в SolidWorks."""
    app = _sw()
    doc = app.GetFirstDocument()
    if doc is None:
        return "Немає відкритих документів."
    doc_types = {1: "Part", 2: "Assembly", 3: "Drawing"}
    active = app.ActiveDoc
    lines = []
    seen = set()
    while doc is not None:
        path = doc.GetPathName()
        title = doc.GetTitle()
        key = path or title
        if key not in seen:
            seen.add(key)
            doc_type = doc_types.get(doc.GetType(), "Unknown")
            is_active = " ← активний" if active and doc.GetTitle() == active.GetTitle() else ""
            saved = "" if doc.GetSaveFlag() else " [не збережено]"
            lines.append(f"[{doc_type}] {title}{saved}{is_active}\n  {path or '(без шляху)'}")
        doc = doc.GetNext()
    return "\n".join(lines)

@mcp.tool()
def sw_activate_document(path: str) -> str:
    """Активувати відкритий документ за шляхом або назвою файлу."""
    app = _sw()
    doc = app.GetFirstDocument()
    while doc is not None:
        if doc.GetPathName() == path or doc.GetTitle() == path:
            errors = app.ActivateDoc3(doc.GetPathName() or doc.GetTitle(), False, 0)
            if errors:
                return f"Помилка активації: код {errors}"
            return f"Активовано: {doc.GetTitle()}"
        doc = doc.GetNext()
    return f"Документ не знайдено: {path}"

@mcp.tool()
def sw_open_document(path: str) -> str:
    """Відкрити документ SW (.sldprt / .sldasm / .slddrw) за повним шляхом."""
    if not os.path.exists(path):
        return f"Файл не знайдено: {path}"
    errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    doc = _sw().OpenDoc6(path, 0, 1, "", errors, warnings)
    if doc is None:
        return f"Не вдалось відкрити: {path} (errors={errors.value})"
    return f"Відкрито: {doc.GetTitle()}"

@mcp.tool()
def sw_close_document(path: str, save: bool = False) -> str:
    """Закрити документ за шляхом або назвою. save=True — зберегти перед закриттям."""
    app = _sw()
    doc = app.GetFirstDocument()
    while doc is not None:
        if doc.GetPathName() == path or doc.GetTitle() == path:
            title = doc.GetTitle()
            if save:
                doc.Save3(1, 0, 0)
            app.CloseDoc(doc.GetPathName() or title)
            return f"Закрито: {title}"
        doc = doc.GetNext()
    return f"Документ не знайдено: {path}"

# ─────────────────────────────────────────
# SOLIDWORKS — ДЕТАЛІ
# ─────────────────────────────────────────

@mcp.tool()
def sw_new_part() -> str:
    """Створити нову деталь."""
    app = _sw()
    path = ""
    try:
        path = app.GetUserPreferenceStringValue(9)
    except Exception:
        pass
    if not path or not os.path.exists(path):
        candidates = [
            r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\Part.PRTDOT",
            r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2023\templates\Part.PRTDOT",
            r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2024\templates\Part.PRTDOT",
            r"C:\ProgramData\SolidWorks\SolidWorks 2022\templates\Part.prtdot",
            r"C:\ProgramData\SolidWorks\SOLIDWORKS 2022\templates\Part.prtdot",
        ]
        path = next((p for p in candidates if os.path.exists(p)), "")
    if not path:
        raise FileNotFoundError("Шаблон Part.prtdot не знайдено. Перевірте Інструменти → Параметри → Розташування файлів → Шаблони документів")
    app.NewDocument(path, 0, 0, 0)
    return "Нова деталь створена"

@mcp.tool()
def sw_set_material(material: str) -> str:
    """
    Встановити матеріал.
    Приклади: 'AISI 304' / 'Plain Carbon Steel' / 'Aluminum 6061'
    """
    db_candidates = [
        r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\lang\english\sldmaterials\solidworks materials.sldmat",
        r"C:\Program Files\SolidWorks Corp\SolidWorks\lang\english\sldmaterials\solidworks materials.sldmat",
    ]
    db = next((p for p in db_candidates if os.path.exists(p)), "solidworks materials.sldmat")
    _doc().SetMaterialPropertyName2("Default", db, material)
    return f"Матеріал: {material}"

@mcp.tool()
def sw_save(filepath: str) -> str:
    """Зберегти поточний документ."""
    _doc().SaveAs3(filepath, 0, 2)
    return f"Збережено: {filepath}"

@mcp.tool()
def sw_get_mass_properties() -> str:
    """Отримати масо-інерційні характеристики поточної деталі."""
    mp = _doc().Extension.CreateMassProperty2()
    if mp is None:
        return "Не вдалось отримати масо-інерційні характеристики."
    mass = mp.Mass
    vol = mp.Volume
    area = mp.SurfaceArea
    density = mp.Density
    cx, cy, cz = mp.CenterOfMass
    return (
        f"Маса:     {mass * 1000:.4f} г\n"
        f"Об'єм:    {vol * 1e6:.4f} см³\n"
        f"Площа:    {area * 1e4:.4f} см²\n"
        f"Щільність:{density / 1000:.4f} г/см³\n"
        f"ЦМ:       X={cx*1000:.3f} Y={cy*1000:.3f} Z={cz*1000:.3f} мм"
    )

@mcp.tool()
def sw_list_features() -> str:
    """Показати список features поточного документа."""
    feat = _doc().FirstFeature()
    if feat is None:
        return "Немає features."
    lines = []
    while feat is not None:
        name = feat.Name
        ftype = feat.GetTypeName2()
        suppressed = " [придушено]" if feat.IsSuppressed2(0, None) else ""
        lines.append(f"{ftype}: {name}{suppressed}")
        feat = feat.GetNextFeature()
    return "\n".join(lines)

@mcp.tool()
def sw_suppress_feature(name: str) -> str:
    """Придушити feature за назвою."""
    feat = _doc().FirstFeature()
    while feat is not None:
        if feat.Name == name:
            feat.SetSuppression2(0, 2, None)
            return f"Придушено: {name}"
        feat = feat.GetNextFeature()
    return f"Feature не знайдено: {name}"

@mcp.tool()
def sw_unsuppress_feature(name: str) -> str:
    """Зняти придушення з feature за назвою."""
    feat = _doc().FirstFeature()
    while feat is not None:
        if feat.Name == name:
            feat.SetSuppression2(1, 2, None)
            return f"Активовано: {name}"
        feat = feat.GetNextFeature()
    return f"Feature не знайдено: {name}"

@mcp.tool()
def sw_rebuild() -> str:
    """Перебудувати поточний документ (Ctrl+B)."""
    result = _doc().ForceRebuild3(False)
    return "Rebuild виконано." if result else "Rebuild завершено з попередженнями."

@mcp.tool()
def sw_extrude(
    width_mm: float,
    height_mm: float,
    depth_mm: float,
    plane: str = "Front Plane"
) -> str:
    """
    Створити прямокутний ескіз і видавити його (Extrude Boss/Base).
    plane: 'Front Plane' / 'Top Plane' / 'Right Plane'
    """
    doc = _doc()
    doc.Extension.SelectByID2(plane, "PLANE", 0, 0, 0, False, 0, None, 0)
    doc.SketchManager.InsertSketch(True)
    w = width_mm / 1000
    h = height_mm / 1000
    doc.SketchManager.CreateCenterRectangle(0, 0, 0, w / 2, h / 2, 0)
    doc.ClearSelection2(True)
    feat = doc.FeatureManager.FeatureExtrusion2(
        True,              # single direction
        False,             # flip
        False,             # normal direction
        0,                 # end condition: blind
        0,                 # end condition dir2 (unused)
        depth_mm / 1000,   # depth dir1 (metres)
        0.0,               # depth dir2
        False, False,      # draft dir1/dir2
        False, False,      # draft inward dir1/dir2
        0.0, 0.0,          # draft angles
        False, False,      # offset reverse
        False, False,      # translate surface
        True,              # merge
        False,             # feature scope
        True,              # auto select
    )
    if feat is None:
        raise RuntimeError("Видавлювання не вдалось. Перевірте ескіз і площину.")
    return f"Видавлено: {width_mm}×{height_mm}×{depth_mm}мм на площині '{plane}'"

@mcp.tool()
def sw_revolve(
    radius_mm: float,
    height_mm: float,
    angle_deg: float = 360.0,
    plane: str = "Front Plane"
) -> str:
    """
    Накреслити прямокутний профіль і обернути навколо осі Y (Revolve Boss/Base).
    radius_mm — відстань від осі до зовнішнього краю
    angle_deg — кут обертання (360 = повне тіло обертання)
    plane     — 'Front Plane' / 'Top Plane' / 'Right Plane'
    """
    import math
    doc = _doc()
    doc.Extension.SelectByID2(plane, "PLANE", 0, 0, 0, False, 0, None, 0)
    doc.SketchManager.InsertSketch(True)

    r = radius_mm / 1000
    h = height_mm / 1000

    # Centerline along Y — axis of revolution
    cl = doc.SketchManager.CreateCenterLine(0, 0, 0, 0, h, 0)

    # Rectangular profile from axis to radius
    doc.SketchManager.CreateLine(0, 0, 0, r, 0, 0)
    doc.SketchManager.CreateLine(r, 0, 0, r, h, 0)
    doc.SketchManager.CreateLine(r, h, 0, 0, h, 0)
    doc.SketchManager.CreateLine(0, h, 0, 0, 0, 0)

    # Select centerline as revolve axis
    doc.ClearSelection2(True)
    cl.Select4(False, None)

    feat = doc.FeatureManager.FeatureRevolve2(
        math.radians(angle_deg),  # angle dir1 (radians)
        0.0,                       # angle dir2
        0,                         # end condition: blind
        0,                         # end condition dir2
        False,                     # thin feature
        False,                     # reverse direction
        False,                     # flip side
        True,                      # merge bodies
        False,                     # feature scope
        True,                      # auto select
        0,                         # thin wall type
        0.0,                       # thin thickness 1
        0.0,                       # thin thickness 2
    )
    if feat is None:
        raise RuntimeError("Обертання не вдалось. Перевірте профіль і площину.")
    return f"Обернено: R{radius_mm}мм H{height_mm}мм {angle_deg}° на '{plane}'"

@mcp.tool()
def sw_fillet(radius_mm: float) -> str:
    """
    Заокруглити виділені ребра поточної деталі (Feature Fillet).
    Виділіть одне або кілька ребер у SolidWorks перед викликом.
    """
    feat = _doc().FeatureManager.FeatureFillet(
        0,                 # options (none)
        radius_mm / 1000,  # R1 — radius in metres
        0.0,               # R2 (unused for constant radius)
        0,                 # constant radius
        0,                 # sub type
        False,             # feature scope
        None,              # use current edge selection
        0.0,               # backup radius
    )
    if feat is None:
        raise RuntimeError("Fillet не вдалось. Виділіть ребра і спробуйте знову.")
    return f"Fillet R{radius_mm}мм виконано."

@mcp.tool()
def sw_chamfer(distance_mm: float, angle_deg: float = 45.0) -> str:
    """
    Зробити фаску на виділених ребрах (Feature Chamfer).
    Виділіть одне або кілька ребер у SolidWorks перед викликом.
    distance_mm — відстань фаски
    angle_deg   — кут фаски (45° = рівностороння фаска)
    """
    import math
    edge_type = 1 if angle_deg == 45.0 else 0   # 1=equal-dist, 0=angle-dist
    param2 = distance_mm / 1000 if angle_deg == 45.0 else math.radians(angle_deg)
    feat = _doc().FeatureManager.InsertFeatureChamfer(
        0,                   # options (none)
        edge_type,
        distance_mm / 1000,  # distance (metres)
        param2,
    )
    if feat is None:
        raise RuntimeError("Chamfer не вдалось. Виділіть ребра і спробуйте знову.")
    return f"Chamfer {distance_mm}мм × {angle_deg}° виконано."

@mcp.tool()
def sw_hole(
    diameter_mm: float,
    depth_mm: float = None,
    x_mm: float = 0.0,
    y_mm: float = 0.0,
    plane: str = "Top Plane"
) -> str:
    """
    Свердлити отвір (Extruded Cut).
    diameter_mm — діаметр отвору
    depth_mm    — глибина (None = наскрізний)
    x_mm, y_mm  — координати центру на площині ескізу
    plane       — 'Top Plane' / 'Front Plane' / 'Right Plane'
    """
    doc = _doc()
    doc.Extension.SelectByID2(plane, "PLANE", 0, 0, 0, False, 0, None, 0)
    doc.SketchManager.InsertSketch(True)

    cx, cy = x_mm / 1000, y_mm / 1000
    r = (diameter_mm / 2) / 1000
    doc.SketchManager.CreateCircle(cx, cy, 0, cx + r, cy, 0)
    doc.ClearSelection2(True)

    through_all = depth_mm is None
    t1 = 1 if through_all else 0          # 1=ThroughAll, 0=Blind
    d1 = 0.0 if through_all else depth_mm / 1000

    feat = doc.FeatureManager.FeatureCut4(
        True,   # single direction
        False,  # flip
        False,  # direction
        t1,     # end condition dir1
        0,      # end condition dir2
        d1,     # depth dir1 (metres)
        0.0,    # depth dir2
        False, False,   # draft dir1/dir2
        False, False,   # draft inward dir1/dir2
        0.0, 0.0,       # draft angles
        False, False,   # offset reverse
        False, False,   # translate surface
        True,           # normal cut
        False,          # feature scope
        True,           # auto select
        False,          # assembly feature scope
        False,          # auto select components
        False,          # propagate to parts
    )
    if feat is None:
        raise RuntimeError("Отвір не вдалось. Перевірте геометрію та площину.")
    depth_str = "наскрізний" if through_all else f"{depth_mm}мм"
    return f"Отвір Ø{diameter_mm}мм {depth_str} на '{plane}' [{x_mm}, {y_mm}]"

@mcp.tool()
def sw_linear_pattern(
    spacing_x_mm: float,
    count_x: int,
    spacing_y_mm: float = 0.0,
    count_y: int = 1,
) -> str:
    """
    Лінійний масив виділеного feature (Linear Pattern).
    Виділіть seed feature в SolidWorks перед викликом.
    spacing_x_mm / count_x — крок і кількість вздовж X
    spacing_y_mm / count_y — крок і кількість вздовж Y (1 = тільки X)
    """
    import math
    feat = _doc().FeatureManager.FeatureLinearPattern(
        spacing_x_mm / 1000,  # D1 — spacing dir1
        0.0,                   # A1 — angle dir1 (along X)
        count_x,               # N1 — count dir1
        spacing_y_mm / 1000,  # D2 — spacing dir2
        math.radians(90.0),    # A2 — angle dir2 (along Y)
        count_y,               # N2 — count dir2
        None,                  # ref axis
        None,                  # seed features (use current selection)
        False,                 # geometry pattern
        False,                 # assembly pattern
    )
    if feat is None:
        raise RuntimeError("Linear Pattern не вдалось. Виділіть feature і спробуйте знову.")
    y_info = f" × {count_y}×{spacing_y_mm}мм" if count_y > 1 else ""
    return f"Linear Pattern: {count_x}×{spacing_x_mm}мм{y_info}"

@mcp.tool()
def sw_circular_pattern(count: int, angle_deg: float = 360.0) -> str:
    """
    Круговий масив виділеного feature (Circular Pattern).
    Виділіть seed feature і вісь обертання в SolidWorks перед викликом.
    count     — кількість екземплярів
    angle_deg — загальний кут (360 = повне коло)
    """
    import math
    feat = _doc().FeatureManager.FeatureCircularPattern4(
        count,                  # number of instances
        math.radians(angle_deg),  # total angle (radians)
        True,                   # equal spacing
        None,                   # ref axis (use current selection)
        None,                   # seed features (use current selection)
        False,                  # geometry pattern
        False,                  # assembly pattern
    )
    if feat is None:
        raise RuntimeError("Circular Pattern не вдалось. Виділіть feature і вісь, потім спробуйте знову.")
    return f"Circular Pattern: {count} екз. на {angle_deg}°"

# ─────────────────────────────────────────
# SOLIDWORKS — ЕСКІЗ
# ─────────────────────────────────────────

@mcp.tool()
def sw_sketch_start(plane: str = "Front Plane") -> str:
    """
    Увійти в режим ескізу на вказаній площині.
    plane: 'Front Plane' / 'Top Plane' / 'Right Plane'
    """
    doc = _doc()
    doc.Extension.SelectByID2(plane, "PLANE", 0, 0, 0, False, 0, None, 0)
    doc.SketchManager.InsertSketch(True)
    return f"Ескіз розпочато на '{plane}'"

@mcp.tool()
def sw_sketch_line(x1_mm: float, y1_mm: float, x2_mm: float, y2_mm: float) -> str:
    """Намалювати лінію в активному ескізі."""
    _doc().SketchManager.CreateLine(x1_mm/1000, y1_mm/1000, 0, x2_mm/1000, y2_mm/1000, 0)
    return f"Лінія: ({x1_mm},{y1_mm}) → ({x2_mm},{y2_mm})мм"

@mcp.tool()
def sw_sketch_circle(cx_mm: float, cy_mm: float, radius_mm: float) -> str:
    """Намалювати коло в активному ескізі."""
    cx, cy, r = cx_mm/1000, cy_mm/1000, radius_mm/1000
    _doc().SketchManager.CreateCircle(cx, cy, 0, cx + r, cy, 0)
    return f"Коло: центр ({cx_mm},{cy_mm}) R{radius_mm}мм"

@mcp.tool()
def sw_sketch_arc(
    cx_mm: float,
    cy_mm: float,
    radius_mm: float,
    start_deg: float,
    end_deg: float,
) -> str:
    """
    Намалювати дугу в активному ескізі.
    start_deg / end_deg — кути від осі X (проти годинникової стрілки).
    """
    import math
    cx, cy, r = cx_mm/1000, cy_mm/1000, radius_mm/1000
    sx = cx + r * math.cos(math.radians(start_deg))
    sy = cy + r * math.sin(math.radians(start_deg))
    ex = cx + r * math.cos(math.radians(end_deg))
    ey = cy + r * math.sin(math.radians(end_deg))
    _doc().SketchManager.CreateArc(cx, cy, 0, sx, sy, 0, ex, ey, 0, 1)
    return f"Дуга: центр ({cx_mm},{cy_mm}) R{radius_mm}мм {start_deg}°→{end_deg}°"

@mcp.tool()
def sw_sketch_finish() -> str:
    """Вийти з режиму ескізу (зберегти ескіз)."""
    _doc().SketchManager.InsertSketch(True)
    return "Ескіз завершено"

# ─────────────────────────────────────────
# SOLIDWORKS — SHEET METAL
# ─────────────────────────────────────────

@mcp.tool()
def sw_base_flange(
    width_mm: float,
    height_mm: float,
    thickness_mm: float,
    bend_radius_mm: float = 1.0
) -> str:
    """Створити базовий фланець листового металу."""
    doc = _doc()
    doc.Extension.SelectByID2("Front Plane", "PLANE", 0, 0, 0, False, 0, None, 0)
    doc.SketchManager.InsertSketch(True)
    w = width_mm / 1000
    h = height_mm / 1000
    doc.SketchManager.CreateCenterRectangle(0, 0, 0, w/2, h/2, 0)
    t = float(thickness_mm / 1000)
    r = float(bend_radius_mm / 1000)
    VR8  = pythoncom.VT_R8
    VI4  = pythoncom.VT_I4
    VBL  = pythoncom.VT_BOOL
    VBS  = pythoncom.VT_BSTR
    V    = win32com.client.VARIANT
    err1 = err2 = None

    try:
        feat = doc.FeatureManager.InsertSheetMetalBaseFlange(
            V(VBL, False), V(VR8, t), V(VR8, r),
            V(VI4, 0), V(VR8, 0.5), V(VBS, ""),
        )
        if feat is not None:
            return f"Фланець: {width_mm}×{height_mm}×{thickness_mm}мм R{bend_radius_mm}"
    except Exception as e:
        err1 = repr(e)

    try:
        feat = doc.FeatureManager.InsertSheetMetalBaseFlange2(
            V(VR8, t),    V(VBL, False), V(VR8, r),
            V(VI4, 0),    V(VR8, 0.5),
            V(VBL, True), V(VI4, 0),    V(VBL, False),
            V(VR8, 0.5),  V(VR8, t),    V(VR8, t),
            V(VBL, False), V(VBS, ""),  V(VBL, False),
        )
        if feat is not None:
            return f"Фланець: {width_mm}×{height_mm}×{thickness_mm}мм R{bend_radius_mm}"
    except Exception as e:
        err2 = repr(e)

    raise RuntimeError(f"v1={err1} | v2={err2}") from None

@mcp.tool()
def sw_export_dxf(filepath: str) -> str:
    """Експортувати розгортку Sheet Metal як DXF."""
    _doc().ExportToDWG2(filepath, "", 1, True, None, False, False, 0, None)
    return f"DXF збережено: {filepath}"

# ─────────────────────────────────────────
# SOLIDWORKS — 3D ДРУК
# ─────────────────────────────────────────

@mcp.tool()
def sw_export_stl(filepath: str, quality: str = "fine") -> str:
    """
    Експорт STL для Bambu P1S.
    quality: 'coarse' / 'fine'
    """
    q = 1 if quality == "fine" else 0
    _sw().SetUserPreferenceIntegerValue(57, q)
    _sw().SetUserPreferenceIntegerValue(56, 0)
    _doc().SaveAs3(filepath, 0, 2)
    return f"STL збережено: {filepath}"

@mcp.tool()
def sw_export_3mf(filepath: str) -> str:
    """Експорт 3MF для Bambu Studio."""
    _doc().SaveAs3(filepath, 0, 2)
    return f"3MF збережено: {filepath}"

@mcp.tool()
def sw_export_step(filepath: str) -> str:
    """Експортувати деталь/збірку як STEP (.step / .stp)."""
    _doc().SaveAs3(filepath, 0, 2)
    return f"STEP збережено: {filepath}"

@mcp.tool()
def sw_export_iges(filepath: str) -> str:
    """Експортувати деталь/збірку як IGES (.iges / .igs)."""
    _doc().SaveAs3(filepath, 0, 2)
    return f"IGES збережено: {filepath}"

@mcp.tool()
def sw_export_pdf(filepath: str) -> str:
    """Експортувати активне креслення як PDF."""
    _doc().SaveAs3(filepath, 0, 2)
    return f"PDF збережено: {filepath}"

# ─────────────────────────────────────────
# SOLIDWORKS — ЗБІРКА
# ─────────────────────────────────────────

@mcp.tool()
def sw_new_assembly() -> str:
    """Створити нову збірку."""
    app = _sw()
    path = ""
    try:
        path = app.GetUserPreferenceStringValue(11)
    except Exception:
        pass
    if not path or not os.path.exists(path):
        candidates = [
            r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\Assembly.ASMDOT",
            r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2023\templates\Assembly.ASMDOT",
            r"C:\ProgramData\SolidWorks\SolidWorks 2022\templates\Assembly.asmdot",
        ]
        path = next((p for p in candidates if os.path.exists(p)), "")
    if not path:
        raise FileNotFoundError("Шаблон Assembly.asmdot не знайдено. Перевірте Інструменти → Параметри → Розташування файлів → Шаблони документів")
    app.NewDocument(path, 0, 0, 0)
    return "Нова збірка створена"

@mcp.tool()
def sw_add_component(
    part_path: str,
    x_mm: float = 0.0,
    y_mm: float = 0.0,
    z_mm: float = 0.0,
) -> str:
    """
    Додати деталь або підзбірку до активної збірки.
    part_path — повний шлях до .sldprt або .sldasm
    """
    if not os.path.exists(part_path):
        return f"Файл не знайдено: {part_path}"
    comp = _doc().AddComponent5(part_path, 0, "", False, "", x_mm/1000, y_mm/1000, z_mm/1000)
    if comp is None:
        raise RuntimeError(f"Не вдалось додати компонент: {part_path}")
    return f"Додано: {os.path.basename(part_path)} [{x_mm}, {y_mm}, {z_mm}]мм"

@mcp.tool()
def sw_add_mate(mate_type: str = "coincident") -> str:
    """
    Додати спряження між двома виділеними сутностями (грані/ребра).
    Виділіть дві сутності в SolidWorks перед викликом.
    mate_type: 'coincident' / 'parallel' / 'perpendicular' / 'concentric' / 'tangent'
    """
    mate_map = {
        "coincident": 0,
        "parallel": 1,
        "perpendicular": 2,
        "tangent": 3,
        "concentric": 4,
        "distance": 5,
        "angle": 6,
    }
    t = mate_map.get(mate_type.lower(), 0)
    mate = _doc().FeatureManager.InsertMate5(
        t, False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, False, False, 0
    )
    if mate is None:
        raise RuntimeError("Спряження не вдалось. Виділіть дві сутності і спробуйте знову.")
    return f"Спряження '{mate_type}' додано."

# ─────────────────────────────────────────
# SOLIDWORKS — КРЕСЛЕННЯ
# ─────────────────────────────────────────

@mcp.tool()
def sw_new_drawing() -> str:
    """Створити нове креслення."""
    app = _sw()
    path = ""
    try:
        path = app.GetUserPreferenceStringValue(12)
    except Exception:
        pass
    if not path or not os.path.exists(path):
        candidates = [
            r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\Drawing.DRWDOT",
            r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2023\templates\Drawing.DRWDOT",
            r"C:\ProgramData\SolidWorks\SolidWorks 2022\templates\Drawing.drwdot",
        ]
        path = next((p for p in candidates if os.path.exists(p)), "")
    if not path:
        raise FileNotFoundError("Шаблон Drawing.drwdot не знайдено. Перевірте Інструменти → Параметри → Розташування файлів → Шаблони документів")
    app.NewDocument(path, 0, 0, 0)
    return "Нове креслення створено"

@mcp.tool()
def sw_add_drawing_view(
    model_path: str,
    view_type: str = "front",
    x_mm: float = 100.0,
    y_mm: float = 150.0,
) -> str:
    """
    Додати вид моделі на активне креслення.
    model_path — шлях до .sldprt або .sldasm
    view_type:  'front' / 'top' / 'right' / 'isometric'
    x_mm, y_mm — позиція виду на аркуші
    """
    view_map = {
        "front":     "*Front",
        "top":       "*Top",
        "right":     "*Right",
        "isometric": "*Isometric",
    }
    view_name = view_map.get(view_type.lower(), "*Front")
    view = _doc().CreateDrawViewFromModelView3(model_path, view_name, x_mm/1000, y_mm/1000, 0)
    if view is None:
        raise RuntimeError("Не вдалось створити вид. Переконайтесь що модель відкрита.")
    return f"Вид '{view_type}' додано на [{x_mm}, {y_mm}]мм"

# ─────────────────────────────────────────
# ARTCAM 2012 — ФРЕЗЕРУВАННЯ
# ─────────────────────────────────────────

@mcp.tool()
def artcam_open(dxf_path: str) -> str:
    """Відкрити DXF в ArtCAM 2012."""
    subprocess.Popen([ARTCAM_EXE, dxf_path])
    return f"ArtCAM 2012 запущено з файлом: {dxf_path}"

@mcp.tool()
def artcam_create_macro(
    art_path: str,
    strategy: str = "profile",
    tool_diameter_mm: float = 6.0,
    depth_mm: float = 10.0,
    pass_depth_mm: float = 2.0,
    feed_rate: float = 1500.0,
    spindle_rpm: int = 18000,
    output_nc: str = None
) -> str:
    """
    Генерує ArtCAM 2012 macro (.bas) для toolpath.
    strategy: 'profile' / 'pocket' / 'contour'
    """
    if output_nc is None:
        output_nc = art_path.replace(".art", ".nc")

    macro = f"""Sub Main()
    Dim oDoc As Document
    Set oDoc = ArtCAM.Documents.Open("{art_path}")

    Dim oTool As New CuttingTool
    oTool.Diameter = {tool_diameter_mm}
    oTool.FeedRate = {feed_rate}
    oTool.PlungeRate = {feed_rate * 0.5}
    oTool.SpindleSpeed = {spindle_rpm}
    oTool.StepDown = {pass_depth_mm}

    Dim oTP As Toolpath
"""
    strategies = {
        "profile": f'    Set oTP = oDoc.Toolpaths.AddProfileToolpath(oTool, {depth_mm})',
        "pocket":  f'    Set oTP = oDoc.Toolpaths.AddPocketToolpath(oTool, {depth_mm})',
        "contour": f'    Set oTP = oDoc.Toolpaths.AddContourToolpath(oTool, {depth_mm})',
    }
    macro += strategies.get(strategy, strategies["profile"])
    macro += f"""
    oTP.Calculate()
    oTP.SaveAsGCode "{output_nc}"

    MsgBox "Готово: {output_nc}"
End Sub"""

    os.makedirs(ARTCAM_MACROS, exist_ok=True)
    macro_path = os.path.join(ARTCAM_MACROS, "toolpath.bas")
    with open(macro_path, "w") as f:
        f.write(macro)

    return f"""Macro готовий: {macro_path}
G-code буде збережено: {output_nc}
→ В ArtCAM: Tools → Run Macro → вибери toolpath.bas"""

@mcp.tool()
def artcam_post_wdmax(nc_path: str) -> str:
    """Додати заголовок WDMAX до G-code файлу."""
    out_path = nc_path.replace(".nc", "_wdmax.nc")
    header = f"""; STUKACH MFG
; WDMAX CNC
; Source: {nc_path}
G21 G90 G17
G94
"""
    with open(nc_path, "r") as f:
        content = f.read()
    with open(out_path, "w") as f:
        f.write(header + content)
    return f"WDMAX файл готовий: {out_path}"

# ─────────────────────────────────────────
# ПОВНИЙ PIPELINE
# ─────────────────────────────────────────

@mcp.tool()
def pipeline_laser(
    width_mm: float,
    height_mm: float,
    thickness_mm: float,
    material: str = "Plain Carbon Steel"
) -> str:
    """SW Sheet Metal → DXF → CypNest (лазер)."""
    name = f"laser_{int(width_mm)}x{int(height_mm)}x{int(thickness_mm)}"
    dxf = os.path.join(WORK_DIR, f"{name}.dxf")
    sldprt = os.path.join(WORK_DIR, f"{name}.sldprt")
    sw_new_part()
    sw_set_material(material)
    sw_base_flange(width_mm, height_mm, thickness_mm)
    sw_save(sldprt)
    sw_export_dxf(dxf)
    return f"Лазер pipeline:\n✓ Деталь\n✓ Матеріал\n✓ Фланець\n✓ DXF → {dxf}"

@mcp.tool()
def pipeline_print(
    width_mm: float,
    height_mm: float,
    thickness_mm: float,
    format: str = "stl"
) -> str:
    """SW Solid → STL/3MF → Bambu P1S."""
    name = f"print_{int(width_mm)}x{int(height_mm)}x{int(thickness_mm)}"
    out = os.path.join(WORK_DIR, f"{name}.{format}")
    sldprt = os.path.join(WORK_DIR, f"{name}.sldprt")
    sw_new_part()
    sw_base_flange(width_mm, height_mm, thickness_mm)
    sw_save(sldprt)
    if format == "stl":
        sw_export_stl(out)
    else:
        sw_export_3mf(out)
    return f"Print pipeline:\n✓ Деталь\n✓ {format.upper()} → {out}"

@mcp.tool()
def pipeline_milling(
    width_mm: float,
    height_mm: float,
    depth_mm: float,
    tool_diameter_mm: float = 6.0,
    strategy: str = "pocket"
) -> str:
    """SW → DXF → ArtCAM macro → G-code → WDMAX."""
    name = f"mill_{int(width_mm)}x{int(height_mm)}x{int(depth_mm)}"
    dxf = os.path.join(WORK_DIR, f"{name}.dxf")
    art = os.path.join(WORK_DIR, f"{name}.art")
    nc = os.path.join(WORK_DIR, f"{name}.nc")
    sldprt = os.path.join(WORK_DIR, f"{name}.sldprt")
    sw_new_part()
    sw_base_flange(width_mm, height_mm, 3.0)
    sw_save(sldprt)
    sw_export_dxf(dxf)
    artcam_open(dxf)
    artcam_create_macro(art, strategy, tool_diameter_mm, depth_mm)
    return f"""Milling pipeline:
✓ SW деталь
✓ DXF → {dxf}
✓ ArtCAM запущено
✓ Macro готовий
→ В ArtCAM: Tools → Run Macro → toolpath.bas
→ Після виконання: artcam_post_wdmax("{nc}")"""

# ─────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
