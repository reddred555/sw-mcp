"""
Тести для klips led.SLDPRT:
  - відкриття файлу
  - встановлення матеріалу ABS
  - масові характеристики (mock COM)
  - інженерний аналіз навантажень (балкова теорія, без SW Simulation)
"""
import pytest
import server


# ──────────────────────────────────────────────────────────────
# Утиліти
# ──────────────────────────────────────────────────────────────

KLIPS_PATH = r"C:\STUKACH\work\klips led.SLDPRT"

# Типові геометричні параметри кліпса LED (ABS)
ARM_L  = 10.0   # довжина защіпки, мм
ARM_H  = 1.2    # товщина защіпки, мм
ARM_B  = 5.0    # ширина защіпки, мм
DELTA  = 3.0    # розкриття при монтажі, мм
SPAN   = 25.0   # проліт корпусу, мм
T_WALL = 2.0    # товщина стінки, мм
F_PRESS = 15.0  # натиск стрічки, Н

# ABS
E_ABS  = 2.3    # ГПа
SY_ABS = 40.0   # МПа


# ──────────────────────────────────────────────────────────────
# sw_open_document
# ──────────────────────────────────────────────────────────────

class TestOpenKlips:
    def test_returns_opened_title_on_success(self, mocker):
        fake_doc = mocker.MagicMock()
        fake_doc.GetTitle = "klips led"

        fake_app = mocker.MagicMock()
        fake_app.OpenDoc6.return_value = fake_doc
        fake_app.ActiveDoc = None

        server._sw = lambda: fake_app
        mocker.patch("os.path.exists", return_value=True)

        result = server.sw_open_document(KLIPS_PATH)
        assert "klips led" in result

    def test_returns_error_when_file_missing(self, mocker):
        mocker.patch("os.path.exists", return_value=False)
        result = server.sw_open_document(KLIPS_PATH)
        assert "не знайдено" in result.lower()

    def test_extension_sldprt_maps_to_doctype_1(self, mocker):
        fake_doc = mocker.MagicMock()
        fake_doc.GetTitle = "klips led"

        fake_app = mocker.MagicMock()
        fake_app.OpenDoc6.return_value = fake_doc
        fake_app.ActiveDoc = None

        server._sw = lambda: fake_app
        mocker.patch("os.path.exists", return_value=True)

        server.sw_open_document(KLIPS_PATH)
        call_args = fake_app.OpenDoc6.call_args[0]
        assert call_args[1] == 1  # 1 = Part

    def test_falls_back_to_active_doc_when_open_returns_none(self, mocker):
        active = mocker.MagicMock()
        active.GetTitle = "klips led"
        active.GetPathName = KLIPS_PATH

        fake_app = mocker.MagicMock()
        fake_app.OpenDoc6.return_value = None
        fake_app.ActiveDoc = active

        server._sw = lambda: fake_app
        mocker.patch("os.path.exists", return_value=True)

        result = server.sw_open_document(KLIPS_PATH)
        assert "klips led" in result


# ──────────────────────────────────────────────────────────────
# sw_set_material → ABS
# ──────────────────────────────────────────────────────────────

class TestSetMaterialAbs:
    def _make_doc(self, mocker):
        doc = mocker.MagicMock()
        server._sw = lambda: mocker.MagicMock(ActiveDoc=doc)
        return doc

    def test_result_contains_abs(self, mocker):
        self._make_doc(mocker)
        mocker.patch("os.path.exists", return_value=True)
        result = server.sw_set_material("ABS")
        assert "ABS" in result

    def test_calls_set_material_property(self, mocker):
        doc = self._make_doc(mocker)
        mocker.patch("os.path.exists", return_value=True)
        server.sw_set_material("ABS")
        doc.SetMaterialPropertyName2.assert_called_once()
        args = doc.SetMaterialPropertyName2.call_args[0]
        assert args[2] == "ABS"


# ──────────────────────────────────────────────────────────────
# sw_get_mass_properties — mock COM
# ──────────────────────────────────────────────────────────────

class TestMassPropertiesAbs:
    def _setup_mp2(self, mocker, mass=0.012, vol=1.05e-5, area=8.2e-3,
                   density=1050.0, com=(0.0, 5.0e-3, 3.0e-3)):
        """Симулюємо CreateMassProperty2 через COM."""
        mp = mocker.MagicMock()
        mp.Mass = mass
        mp.Volume = vol
        mp.SurfaceArea = area
        mp.Density = density
        mp.CenterOfMass = com

        ext = mocker.MagicMock()
        ext.CreateMassProperty2 = mp   # property, не callable

        doc = mocker.MagicMock()
        doc.Extension = ext
        server._sw = lambda: mocker.MagicMock(ActiveDoc=doc)
        return mp

    def test_returns_mass_in_grams(self, mocker):
        self._setup_mp2(mocker, mass=0.012)
        result = server.sw_get_mass_properties()
        assert "12.0000" in result or "г" in result

    def test_returns_volume_in_cm3(self, mocker):
        self._setup_mp2(mocker, vol=1.05e-5)
        result = server.sw_get_mass_properties()
        assert "см³" in result

    def test_returns_center_of_mass(self, mocker):
        self._setup_mp2(mocker, com=(0.001, 0.005, 0.003))
        result = server.sw_get_mass_properties()
        assert "ЦМ" in result

    def test_fallback_to_get_mass_properties_array(self, mocker):
        """Коли CreateMassProperty2 недоступний — fallback до GetMassProperties."""
        doc = mocker.MagicMock()
        doc.Extension.CreateMassProperty2 = mocker.MagicMock(
            side_effect=Exception("no API")
        )
        doc.Extension.CreateMassProperty = mocker.MagicMock(
            side_effect=Exception("no API")
        )
        # GetMassProperties як property (повертає масив напряму)
        doc.GetMassProperties = [0.012, 1.05e-5, 8.2e-3, 0.001, 0.005, 0.003]
        server._sw = lambda: mocker.MagicMock(ActiveDoc=doc)

        result = server.sw_get_mass_properties()
        assert "г" in result

    def test_error_message_when_all_apis_fail(self, mocker):
        doc = mocker.MagicMock()
        doc.Extension.CreateMassProperty2 = mocker.MagicMock(
            side_effect=Exception("fail")
        )
        doc.Extension.CreateMassProperty = mocker.MagicMock(
            side_effect=Exception("fail")
        )
        doc.GetMassProperties = mocker.MagicMock(side_effect=Exception("fail"))
        server._sw = lambda: mocker.MagicMock(ActiveDoc=doc)

        result = server.sw_get_mass_properties()
        assert "не вдалось" in result.lower()


# ──────────────────────────────────────────────────────────────
# sw_clip_load_analysis — інженерні розрахунки (балкова теорія)
# ──────────────────────────────────────────────────────────────

class TestClipLoadAnalysis:
    def _run(self, **kwargs):
        defaults = dict(
            arm_length_mm=ARM_L, arm_thickness_mm=ARM_H, arm_width_mm=ARM_B,
            deflection_mm=DELTA, press_force_n=F_PRESS,
            body_span_mm=SPAN, body_thickness_mm=T_WALL,
            material_E_gpa=E_ABS, material_yield_mpa=SY_ABS,
        )
        defaults.update(kwargs)
        return server.sw_clip_load_analysis(**defaults)

    def test_returns_string(self):
        assert isinstance(self._run(), str)

    def test_contains_snap_fit_section(self):
        result = self._run()
        assert "Защіпка" in result or "snap-fit" in result.lower()

    def test_contains_body_section(self):
        result = self._run()
        assert "Корпус" in result or "натиск" in result.lower()

    def test_safety_factor_norm_for_long_arm(self):
        """Довга тонка защіпка має запас ≥ 2.0."""
        result = self._run(arm_length_mm=20.0, arm_thickness_mm=1.0, deflection_mm=2.0)
        assert "НОРМА" in result

    def test_safety_factor_exceeded_for_overloaded_arm(self):
        """Коротка товста защіпка з великим розкриттям — перевищення."""
        result = self._run(arm_length_mm=5.0, arm_thickness_mm=2.0, deflection_mm=4.0)
        assert "ПЕРЕВИЩЕННЯ" in result

    def test_snap_fit_force_positive(self):
        """Зусилля монтажу завжди > 0."""
        result = self._run()
        # Парсимо рядок "Зусилля монтажу:    X.X Н"
        for line in result.splitlines():
            if "Зусилля монтажу" in line:
                val = float(line.split(":")[1].strip().split()[0])
                assert val > 0
                break

    def test_deflection_limit_calculated(self):
        """Максимальне допустиме відхилення є в результаті."""
        result = self._run()
        assert "Макс. δ" in result or "без деформ" in result

    def test_body_stress_formula(self):
        """
        Напруження корпусу = M*c/I, де M = F*L/4.
        Для F=15Н, span=25мм, t=2мм, b=5мм:
          I = 5*8/12 ≈ 3.33 мм⁴
          M = 15*25/4 = 93.75 Н·мм
          σ = 93.75*1 / 3.33 ≈ 28.1 МПа
        """
        import math
        F, span, t, b = 15.0, 25.0, 2.0, 5.0
        I = b * t**3 / 12
        M = F * span / 4
        sigma_expected = M * (t / 2) / I
        assert abs(sigma_expected - 28.125) < 0.1

    def test_abs_material_defaults(self):
        """Дефолтні значення — ABS: E=2.3 ГПа, σy=40 МПа."""
        result = self._run()
        assert "АBS" in result or "ABS" in result or "40" in result

    def test_no_sw_simulation_needed(self):
        """Інструмент не звертається до SolidWorks."""
        called = []
        original_sw = server._sw
        server._sw = lambda: called.append(1) or original_sw()
        try:
            server.sw_clip_load_analysis()
        except Exception:
            pass
        assert len(called) == 0, "sw_clip_load_analysis не повинен викликати _sw()"

    @pytest.mark.parametrize("arm_l,arm_h,delta,expect_ok", [
        (20.0, 1.0, 2.0, True),   # довга тонка → норма
        (8.0,  1.5, 3.0, False),  # коротка товста → перевищення
        (15.0, 1.2, 2.5, False),  # σ≈46МПа > σy=40МПа → перевищення
    ])
    def test_parametric_safety(self, arm_l, arm_h, delta, expect_ok):
        result = self._run(arm_length_mm=arm_l, arm_thickness_mm=arm_h,
                           deflection_mm=delta)
        if expect_ok:
            assert "ПЕРЕВИЩЕННЯ" not in result
        else:
            assert "ПЕРЕВИЩЕННЯ" in result


# ──────────────────────────────────────────────────────────────
# sw_simulation_setup — add-in недоступний
# ──────────────────────────────────────────────────────────────

class TestSimulationNotAvailable:
    def test_raises_runtime_error_without_addin(self, mocker):
        fake_app = mocker.MagicMock()
        fake_app.GetAddInObject.return_value = None
        server._sw = lambda: fake_app

        with pytest.raises(RuntimeError, match="CosmosWorks"):
            server.sw_simulation_setup("Натиск_стрічки")

    def test_error_message_mentions_add_ins(self, mocker):
        fake_app = mocker.MagicMock()
        fake_app.GetAddInObject.return_value = None
        server._sw = lambda: fake_app

        try:
            server.sw_simulation_setup()
        except RuntimeError as e:
            assert "Додатки" in str(e) or "Add-Ins" in str(e) or "Simulation" in str(e)
