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
swApp = None

ARTCAM_EXE = r"C:\Program Files\ArtCAM 2012\ArtCAM.exe"
ARTCAM_MACROS = r"C:\STUKACH\sw-mcp\artcam_macros"
WORK_DIR = r"C:\STUKACH\work"
DOCS_DIR = r"C:\STUKACH\sw-mcp\docs"

def _doc():
    doc = swApp.ActiveDoc
    if doc is None:
        raise RuntimeError("Немає активного документа. Відкрийте або створіть деталь.")
    return doc

# ─────────────────────────────────────────
# SOLIDWORKS — З'ЄДНАННЯ
# ─────────────────────────────────────────

@mcp.tool()
def sw_connect() -> str:
    """Підключитись до запущеного SolidWorks."""
    global swApp
    pythoncom.CoInitialize()
    swApp = win32com.client.Dispatch("SldWorks.Application")
    swApp.Visible = True
    return f"SolidWorks підключено. Версія: {swApp.RevisionNumber}"

@mcp.tool()
def sw_list_documents() -> str:
    """Показати всі відкриті документи в SolidWorks."""
    doc = swApp.GetFirstDocument()
    if doc is None:
        return "Немає відкритих документів."
    doc_types = {1: "Part", 2: "Assembly", 3: "Drawing"}
    active = swApp.ActiveDoc
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
    doc = swApp.GetFirstDocument()
    while doc is not None:
        if doc.GetPathName() == path or doc.GetTitle() == path:
            errors = swApp.ActivateDoc3(doc.GetPathName() or doc.GetTitle(), False, 0)
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
    doc = swApp.OpenDoc6(path, 0, 1, "", errors, warnings)
    if doc is None:
        return f"Не вдалось відкрити: {path} (errors={errors.value})"
    return f"Відкрито: {doc.GetTitle()}"

@mcp.tool()
def sw_close_document(path: str, save: bool = False) -> str:
    """Закрити документ за шляхом або назвою. save=True — зберегти перед закриттям."""
    doc = swApp.GetFirstDocument()
    while doc is not None:
        if doc.GetPathName() == path or doc.GetTitle() == path:
            title = doc.GetTitle()
            if save:
                doc.Save3(1, 0, 0)
            swApp.CloseDoc(doc.GetPathName() or title)
            return f"Закрито: {title}"
        doc = doc.GetNext()
    return f"Документ не знайдено: {path}"

# ─────────────────────────────────────────
# SOLIDWORKS — ДЕТАЛІ
# ─────────────────────────────────────────

@mcp.tool()
def sw_new_part() -> str:
    """Створити нову деталь."""
    path = ""
    try:
        path = swApp.GetUserPreferenceStringValue(9)
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
    swApp.NewDocument(path, 0, 0, 0)
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

# ─────────────────────────────────────────
# SOLIDWORKS — ЗБІРКИ (ASSEMBLY)
# ─────────────────────────────────────────

@mcp.tool()
def sw_new_assembly() -> str:
    """Створити новий документ збірки (.sldasm)."""
    candidates = [
        r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2022\templates\Assembly.ASMDOT",
        r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2023\templates\Assembly.ASMDOT",
        r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2024\templates\Assembly.ASMDOT",
        r"C:\ProgramData\SolidWorks\SolidWorks 2022\templates\Assembly.asmdot",
    ]
    try:
        path = swApp.GetUserPreferenceStringValue(10)
    except Exception:
        path = ""
    if not path or not os.path.exists(path):
        path = next((p for p in candidates if os.path.exists(p)), "")
    if not path:
        raise FileNotFoundError(
            "Шаблон Assembly.asmdot не знайдено. "
            "Перевірте Інструменти → Параметри → Розташування файлів → Шаблони документів"
        )
    swApp.NewDocument(path, 0, 0, 0)
    return "Нова збірка створена"


@mcp.tool()
def sw_add_component(
    part_path: str,
    x_mm: float = 0.0,
    y_mm: float = 0.0,
    z_mm: float = 0.0
) -> str:
    """
    Додати компонент до активної збірки.
    part_path — повний шлях до .sldprt або .sldasm
    x_mm, y_mm, z_mm — положення в мм відносно початку координат збірки
    """
    if not os.path.exists(part_path):
        return f"Файл не знайдено: {part_path}"
    asm = _doc()
    # AddComponent5: path, configOption, configName, alignWithFixed, x, y, z  (coords in metres)
    comp = asm.AddComponent5(part_path, 0, "", False, x_mm / 1000, y_mm / 1000, z_mm / 1000)
    if comp is None:
        raise RuntimeError(f"SolidWorks не зміг вставити компонент: {part_path}")
    return f"Компонент додано: {os.path.basename(part_path)} @ ({x_mm}, {y_mm}, {z_mm}) мм"


@mcp.tool()
def sw_add_mate(
    mate_type: str,
    entity1: str = "",
    entity2: str = ""
) -> str:
    """
    Додати спряження (mate) між двома об'єктами збірки.
    mate_type: 'coincident' | 'parallel' | 'perpendicular' | 'concentric' | 'distance' | 'angle'
    entity1, entity2 — назви граней/осей для SelectByID2
    """
    # swMateType_e values from SolidWorks API
    MATE_TYPES = {
        "coincident":    0,
        "parallel":      1,
        "perpendicular": 2,
        "concentric":    4,
        "distance":      5,
        "angle":         6,
    }
    code = MATE_TYPES.get(mate_type.lower(), 0)
    asm = _doc()
    if entity1:
        asm.Extension.SelectByID2(entity1, "FACE", 0, 0, 0, False, 1, None, 0)
    if entity2:
        asm.Extension.SelectByID2(entity2, "FACE", 0, 0, 0, True, 1, None, 0)
    mate = asm.FeatureManager.InsertMate5(code, False, 0, 0, 0, 0, 0, 0, 0, 0, 0, False, False, 0, 0)
    if mate is None:
        raise RuntimeError(f"Не вдалось створити спряження '{mate_type}'")
    label = entity1 and entity2 and f" між {entity1} ↔ {entity2}" or ""
    return f"Спряження '{mate_type}'{label} додано"


@mcp.tool()
def sw_list_components() -> str:
    """Показати всі компоненти активної збірки."""
    asm = _doc()
    comps = asm.GetComponents(False)
    if not comps:
        return "Збірка порожня або не є збіркою."
    lines = []
    for comp in comps:
        name = comp.Name2
        path = comp.GetPathName()
        suppressed = " [придушено]" if comp.IsSuppressed() else ""
        lines.append(f"  {name}{suppressed}\n    {path or '(без шляху)'}")
    return f"Компонентів: {len(comps)}\n" + "\n".join(lines)


@mcp.tool()
def sw_save_assembly(filepath: str) -> str:
    """Зберегти активну збірку як .sldasm."""
    _doc().SaveAs3(filepath, 0, 2)
    return f"Збірка збережена: {filepath}"

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
    doc.FeatureManager.InsertSheetMetalBaseFlange2(
        thickness_mm / 1000,   # Thickness
        False,                 # bFlipSide
        bend_radius_mm / 1000, # BendRadius
        0,                     # BendAllowanceType
        0.0,                   # BendAllowanceValue
        True,                  # bUseDefaultRelief
        0,                     # ReliefType
        False,                 # bUseReliefRatio
        0.0,                   # dReliefRatio
        0.0,                   # dReliefWidth
        0.0,                   # dReliefDepth
        False,                 # bAutoReliefRatio
        "",                    # GaugeTable
        False                  # bDirection
    )
    return f"Фланець: {width_mm}×{height_mm}×{thickness_mm}мм R{bend_radius_mm}"

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
    swApp.SetUserPreferenceIntegerValue(57, q)
    swApp.SetUserPreferenceIntegerValue(56, 0)
    _doc().SaveAs3(filepath, 0, 2)
    return f"STL збережено: {filepath}"

@mcp.tool()
def sw_export_3mf(filepath: str) -> str:
    """Експорт 3MF для Bambu Studio."""
    _doc().SaveAs3(filepath, 0, 2)
    return f"3MF збережено: {filepath}"

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
# DXF ДІАГНОСТИКА
# ─────────────────────────────────────────

@mcp.tool()
def analyze_dxf(filepath: str) -> str:
    """
    Аналіз DXF-файлу: підрахунок примітивів, габарити, кола, перевірка.
    Підтримує ASCII DXF (AutoCAD R2000+, SolidWorks export).
    """
    if not os.path.exists(filepath):
        return f"Файл не знайдено: {filepath}"

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = [l.rstrip("\n\r") for l in f]
    except OSError as exc:
        return f"Помилка читання: {exc}"

    # Parse group-code pairs
    pairs = []
    i = 0
    while i + 1 < len(lines):
        try:
            code = int(lines[i].strip())
        except ValueError:
            i += 1
            continue
        pairs.append((code, lines[i + 1].strip()))
        i += 2

    # Locate ENTITIES section
    in_entities = False
    entity_pairs = []
    j = 0
    while j < len(pairs):
        code, val = pairs[j]
        if code == 0 and val == "SECTION":
            if j + 1 < len(pairs) and pairs[j + 1] == (2, "ENTITIES"):
                in_entities = True
                j += 2
                continue
        if in_entities:
            if code == 0 and val == "ENDSEC":
                break
            entity_pairs.append((code, val))
        j += 1

    if not entity_pairs:
        return f"Секція ENTITIES не знайдена або порожня: {filepath}"

    # Walk entities
    counts: dict[str, int] = {}
    circles: list[dict] = []
    xs: list[float] = []
    ys: list[float] = []
    lines_geom: list[dict] = []

    current: dict | None = None
    for code, val in entity_pairs:
        if code == 0:
            if current is not None:
                _finalize_entity(current, circles, lines_geom, xs, ys)
            etype = val
            counts[etype] = counts.get(etype, 0) + 1
            current = {"type": etype}
        elif current is not None:
            _store_coord(current, code, val, xs, ys)
    if current is not None:
        _finalize_entity(current, circles, lines_geom, xs, ys)

    # Build report
    total = sum(counts.values())
    lines_out = [f"DXF: {os.path.basename(filepath)}", f"Всього примітивів: {total}", ""]

    lines_out.append("Типи:")
    for etype, cnt in sorted(counts.items()):
        lines_out.append(f"  {etype}: {cnt}")

    if xs and ys:
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        lines_out.append(f"\nГабарит (XY): {x1 - x0:.3f} × {y1 - y0:.3f} мм")
        lines_out.append(f"  X [{x0:.3f} … {x1:.3f}]")
        lines_out.append(f"  Y [{y0:.3f} … {y1:.3f}]")

    if circles:
        lines_out.append(f"\nКола ({len(circles)}):")
        for c in circles:
            lines_out.append(f"  R={c['r']:.3f}  cx={c['cx']:.3f}  cy={c['cy']:.3f}")

    if not counts:
        lines_out.append("\n[!] Геометрія не виявлена")

    return "\n".join(lines_out)


def _store_coord(entity: dict, code: int, val: str, xs: list, ys: list) -> None:
    try:
        fval = float(val)
    except ValueError:
        return
    entity[code] = fval
    if code == 10:
        xs.append(fval)
    elif code == 20:
        ys.append(fval)
    elif code == 11:
        xs.append(fval)
    elif code == 21:
        ys.append(fval)
    elif code == 40 and entity.get("type") in ("CIRCLE", "ARC"):
        pass  # radius, handled in finalize


def _finalize_entity(entity: dict, circles: list, lines_geom: list, xs: list, ys: list) -> None:
    etype = entity.get("type")
    if etype == "CIRCLE":
        r = entity.get(40, 0.0)
        cx = entity.get(10, 0.0)
        cy = entity.get(20, 0.0)
        circles.append({"r": r, "cx": cx, "cy": cy})
        # Add bounding box of circle
        xs.extend([cx - r, cx + r])
        ys.extend([cy - r, cy + r])
    elif etype == "ARC":
        r = entity.get(40, 0.0)
        cx = entity.get(10, 0.0)
        cy = entity.get(20, 0.0)
        # Approximate with center ± radius
        xs.extend([cx - r, cx + r])
        ys.extend([cy - r, cy + r])


# ─────────────────────────────────────────
# RESOURCES — проектна документація
# ─────────────────────────────────────────

@mcp.resource("docs://drever/spec")
def drever_spec() -> str:
    """Технічний звіт Drever Ingeniering — LED ручка з touch+mmWave."""
    path = os.path.join(DOCS_DIR, "drever_ingeniering_v1.md")
    with open(path, encoding="utf-8") as f:
        return f.read()

# ─────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
