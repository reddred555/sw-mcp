# STUKACH MFG MCP Server

SolidWorks 2022 + ArtCAM 2012 — MCP-сервер для автоматизації виробничого pipeline.

## Pipeline

```
SolidWorks → DXF/STL/3MF → ArtCAM → G-code → WDMAX CNC
```

## Інструменти

### SolidWorks — З'єднання
| Інструмент | Опис |
|---|---|
| `sw_connect()` | Підключитись до запущеного SolidWorks |

### SolidWorks — Документи
| Інструмент | Опис |
|---|---|
| `sw_list_documents()` | Список всіх відкритих документів |
| `sw_open_document(path)` | Відкрити файл `.sldprt` / `.sldasm` / `.slddrw` |
| `sw_activate_document(path)` | Активувати відкритий документ |
| `sw_close_document(path, save=False)` | Закрити документ |

### SolidWorks — Деталі
| Інструмент | Опис |
|---|---|
| `sw_new_part()` | Створити нову деталь |
| `sw_set_material(material)` | Встановити матеріал (`AISI 304`, `Aluminum 6061`, ...) |
| `sw_save(filepath)` | Зберегти документ |
| `sw_get_mass_properties()` | Маса, об'єм, площа, щільність, центр мас |

### SolidWorks — Sheet Metal
| Інструмент | Опис |
|---|---|
| `sw_base_flange(width_mm, height_mm, thickness_mm, bend_radius_mm)` | Створити базовий фланець |
| `sw_export_dxf(filepath)` | Експортувати розгортку як DXF |

### SolidWorks — 3D Друк
| Інструмент | Опис |
|---|---|
| `sw_export_stl(filepath, quality)` | Експорт STL для Bambu P1S |
| `sw_export_3mf(filepath)` | Експорт 3MF для Bambu Studio |

### ArtCAM 2012
| Інструмент | Опис |
|---|---|
| `artcam_open(dxf_path)` | Відкрити DXF в ArtCAM 2012 |
| `artcam_create_macro(art_path, strategy, ...)` | Генерувати macro для toolpath (`profile` / `pocket` / `contour`) |
| `artcam_post_wdmax(nc_path)` | Додати заголовок WDMAX до G-code |

### Pipelines
| Інструмент | Опис |
|---|---|
| `pipeline_laser(width_mm, height_mm, thickness_mm, material)` | SW Sheet Metal → DXF → CypNest |
| `pipeline_print(width_mm, height_mm, thickness_mm, format)` | SW → STL/3MF → Bambu P1S |
| `pipeline_milling(width_mm, height_mm, depth_mm, tool_diameter_mm, strategy)` | SW → DXF → ArtCAM → G-code → WDMAX |

## Встановлення

```bash
pip install fastmcp pywin32
```

## Запуск

```bash
python server.py
```

## Вимоги

- Windows
- SolidWorks 2022
- ArtCAM 2012 (`C:\Program Files\ArtCAM 2012\ArtCAM.exe`)
- Робоча директорія: `C:\STUKACH\work`
