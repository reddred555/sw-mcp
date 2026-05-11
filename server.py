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
currentDoc = None

ARTCAM_EXE = r"C:\Program Files\ArtCAM 2012\ArtCAM.exe"
ARTCAM_MACROS = r"C:\STUKACH\sw-mcp\artcam_macros"
WORK_DIR = r"C:\STUKACH\work"

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
    lines = []
    seen = set()
    while doc is not None:
        path = doc.GetPathName()
        title = doc.GetTitle()
        key = path or title
        if key not in seen:
            seen.add(key)
            doc_type = doc_types.get(doc.GetType(), "Unknown")
            active = " ← активний" if doc == currentDoc else ""
            saved = "" if doc.GetSaveFlag() else " [не збережено]"
            lines.append(f"[{doc_type}] {title}{saved}{active}\n  {path or '(без шляху)'}")
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
            global currentDoc
            currentDoc = doc
            return f"Активовано: {doc.GetTitle()}"
        doc = doc.GetNext()
    return f"Документ не знайдено: {path}"

@mcp.tool()
def sw_open_document(path: str) -> str:
    """Відкрити документ SW (.sldprt / .sldasm / .slddrw) за повним шляхом."""
    global currentDoc
    if not os.path.exists(path):
        return f"Файл не знайдено: {path}"
    errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    doc = swApp.OpenDoc6(path, 0, 1, "", errors, warnings)
    if doc is None:
        return f"Не вдалось відкрити: {path} (errors={errors.value})"
    currentDoc = doc
    return f"Відкрито: {doc.GetTitle()}"

@mcp.tool()
def sw_close_document(path: str, save: bool = False) -> str:
    """Закрити документ за шляхом або назвою. save=True — зберегти перед закриттям."""
    global currentDoc
    doc = swApp.GetFirstDocument()
    while doc is not None:
        if doc.GetPathName() == path or doc.GetTitle() == path:
            title = doc.GetTitle()
            if save:
                doc.Save3(1, 0, 0)
            swApp.CloseDoc(doc.GetPathName() or title)
            if currentDoc and (currentDoc.GetPathName() == path or currentDoc.GetTitle() == path):
                currentDoc = None
            return f"Закрито: {title}"
        doc = doc.GetNext()
    return f"Документ не знайдено: {path}"

# ─────────────────────────────────────────
# SOLIDWORKS — ДЕТАЛІ
# ─────────────────────────────────────────

@mcp.tool()
def sw_new_part() -> str:
    """Створити нову деталь."""
    global currentDoc
    # swDefaultTemplatePart (9) повертає повний шлях до файлу шаблону
    path = swApp.GetUserPreferenceStringValue(9)
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
    currentDoc = swApp.NewDocument(path, 0, 0, 0)
    return "Нова деталь створена"

@mcp.tool()
def sw_set_material(material: str) -> str:
    """
    Встановити матеріал.
    Приклади: 'AISI 304' / 'Plain Carbon Steel' / 'Aluminum 6061'
    """
    currentDoc.SetMaterialPropertyName2(
        "Default", "solidworks materials.sldmat", material
    )
    return f"Матеріал: {material}"

@mcp.tool()
def sw_save(filepath: str) -> str:
    """Зберегти поточний документ."""
    currentDoc.SaveAs3(filepath, 0, 2)
    return f"Збережено: {filepath}"

@mcp.tool()
def sw_get_mass_properties() -> str:
    """Отримати масо-інерційні характеристики поточної деталі."""
    ext = currentDoc.Extension
    status = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    mp = ext.CreateMassProperty2()
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
    feat = currentDoc.FirstFeature()
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
    currentDoc.Extension.SelectByID2(
        "Front Plane", "PLANE", 0, 0, 0, False, 0, None, 0
    )
    currentDoc.SketchManager.InsertSketch(True)
    w = width_mm / 1000
    h = height_mm / 1000
    currentDoc.SketchManager.CreateCenterRectangle(0, 0, 0, w/2, h/2, 0)
    currentDoc.FeatureManager.InsertSheetMetalBaseFlange2(
        thickness_mm / 1000,   # Thickness
        False,                 # bFlipSide
        bend_radius_mm / 1000, # BendRadius
        0,                     # BendAllowanceType (Long)
        0.0,                   # BendAllowanceValue (Double)
        True,                  # bUseDefaultRelief (Boolean)
        0,                     # ReliefType (Long)
        False,                 # bUseReliefRatio (Boolean)
        0.0,                   # dReliefRatio (Double)
        0.0,                   # dReliefWidth (Double)
        0.0,                   # dReliefDepth (Double)
        False,                 # bAutoReliefRatio (Boolean)
        "",                    # GaugeTable (String)
        False                  # bDirection (Boolean)
    )
    return f"Фланець: {width_mm}×{height_mm}×{thickness_mm}мм R{bend_radius_mm}"

@mcp.tool()
def sw_export_dxf(filepath: str) -> str:
    """Експортувати розгортку Sheet Metal як DXF."""
    currentDoc.ExportToDWG2(
        filepath, "", 1, True, None, False, False, 0, None
    )
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
    currentDoc.SaveAs3(filepath, 0, 2)
    return f"STL збережено: {filepath}"

@mcp.tool()
def sw_export_3mf(filepath: str) -> str:
    """Експорт 3MF для Bambu Studio."""
    currentDoc.SaveAs3(filepath, 0, 2)
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
if __name__ == "__main__":
    mcp.run()