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
| `sw_list_features()` | Список features з типом і статусом (придушено/активно) |
| `sw_rebuild()` | Перебудувати документ (Ctrl+B) |
| `sw_suppress_feature(name)` | Придушити feature за назвою |
| `sw_unsuppress_feature(name)` | Зняти придушення з feature за назвою |
| `sw_rename_feature(old_name, new_name)` | Перейменувати feature за назвою |
| `sw_rename_plane(old_name, new_name)` | Перейменувати площину за назвою |
| `sw_rename_axis(old_name, new_name)` | Перейменувати вісь за назвою |
| `sw_rename_coordinate_system(old_name, new_name)` | Перейменувати систему координат за назвою |
| `sw_rename_point(old_name, new_name)` | Перейменувати точку за назвою |
| `sw_rename_weldment_profile(old_name, new_name)` | Перейменувати профіль зварної конструкції за назвою |
| `sw_rename_cut_list_item(old_name, new_name)` | Перейменувати елемент списку вирізів за назвою |
| `sw_rename_body(old_name, new_name)` | Перейменувати тіло деталі за назвою |
| `sw_rename_sketch(old_name, new_name)` | Перейменувати ескіз за назвою |
| `sw_extrude(width_mm, height_mm, depth_mm, plane)` | Прямокутний ескіз + Extrude Boss/Base |
| `sw_revolve(radius_mm, height_mm, angle_deg, plane)` | Прямокутний профіль + Revolve Boss/Base |
| `sw_fillet(radius_mm)` | Заокруглити виділені ребра (Feature Fillet) |
| `sw_chamfer(distance_mm, angle_deg)` | Фаска на виділених ребрах (Feature Chamfer) |
| `sw_hole(diameter_mm, depth_mm, x_mm, y_mm, plane)` | Свердлити отвір (Extruded Cut) |
| `sw_linear_pattern(spacing_x_mm, count_x, spacing_y_mm, count_y)` | Лінійний масив виділеного feature |
| `sw_circular_pattern(count, angle_deg)` | Круговий масив виділеного feature + осі |
| `sw_sweep()` | Sweep Boss/Base по виділених профілі та шляху |
| `sw_loft()` | Loft Boss/Base по виділених профілях (мін. 2) |

### SolidWorks — Ескіз
| Інструмент | Опис |
|---|---|
| `sw_sketch_start(plane)` | Увійти в режим ескізу на площині |
| `sw_sketch_line(x1_mm, y1_mm, x2_mm, y2_mm)` | Намалювати лінію |
| `sw_sketch_circle(cx_mm, cy_mm, radius_mm)` | Намалювати коло |
| `sw_sketch_arc(cx_mm, cy_mm, radius_mm, start_deg, end_deg)` | Намалювати дугу |
| `sw_sketch_finish()` | Вийти з режиму ескізу |

### SolidWorks — Властивості
| Інструмент | Опис |
|---|---|
| `sw_set_property(name, value, config)` | Встановити властивість документа (артикул, опис, ...) |
| `sw_get_property(name, config)` | Отримати значення властивості |
| `sw_list_properties(config)` | Показати всі властивості |

### SolidWorks — Конфігурації
| Інструмент | Опис |
|---|---|
| `sw_list_configurations()` | Список усіх конфігурацій |
| `sw_add_configuration(name, description)` | Додати нову конфігурацію |
| `sw_switch_configuration(name)` | Активувати конфігурацію |
| `sw_rename_configuration(old_name, new_name)` | Перейменувати конфігурацію |
| `sw_delete_configuration(name)` | Видалити конфігурацію |

### SolidWorks — Sheet Metal
| Інструмент | Опис |
|---|---|
| `sw_base_flange(width_mm, height_mm, thickness_mm, bend_radius_mm)` | Створити базовий фланець |
| `sw_edge_flange(height_mm, angle_deg, bend_radius_mm)` | Відгин на виділеному ребрі |
| `sw_flat_pattern(show)` | Показати/приховати розгортку |
| `sw_export_dxf(filepath)` | Експортувати розгортку як DXF |

### SolidWorks — 3D Друк та Експорт
| Інструмент | Опис |
|---|---|
| `sw_export_stl(filepath, quality)` | Експорт STL для Bambu P1S |
| `sw_export_3mf(filepath)` | Експорт 3MF для Bambu Studio |
| `sw_export_step(filepath)` | Експорт STEP (.step / .stp) |
| `sw_export_iges(filepath)` | Експорт IGES (.iges / .igs) |
| `sw_export_pdf(filepath)` | Експорт PDF (креслення) |

### SolidWorks — Збірка
| Інструмент | Опис |
|---|---|
| `sw_new_assembly()` | Створити нову збірку |
| `sw_add_component(part_path, x_mm, y_mm, z_mm)` | Додати деталь або підзбірку |
| `sw_rename_component(old_name, new_name)` | Перейменувати компонент у збірці (наприклад `Part1-1`) |
| `sw_rename_mate(old_name, new_name)` | Перейменувати спряження у збірці |
| `sw_add_mate(mate_type)` | Спряження між виділеними сутностями (`coincident` / `parallel` / ...) |
| `sw_get_bom()` | BOM зі збірки — перелік компонентів з кількостями |

### SolidWorks — Креслення
| Інструмент | Опис |
|---|---|
| `sw_new_drawing()` | Створити нове креслення |
| `sw_add_drawing_view(model_path, view_type, x_mm, y_mm)` | Додати вид моделі (`front` / `top` / `right` / `isometric`) |
| `sw_rename_sheet(old_name, new_name)` | Перейменувати аркуш креслення |
| `sw_rename_drawing_view(old_name, new_name)` | Перейменувати вид на активному кресленні |
| `sw_add_smart_dimension()` | Додати розмір до виділених сутностей |

### SolidWorks — Симуляція
| Інструмент | Опис |
|---|---|
| `sw_simulation_setup(study_name)` | Створити статичне дослідження (потребує SW Simulation) |
| `sw_simulation_run(study_name)` | Запустити розрахунок |
| `sw_simulation_results(study_name)` | Результати: напруження, переміщення, запас міцності |

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
- SolidWorks Simulation (опційно, для `sw_simulation_*`)
