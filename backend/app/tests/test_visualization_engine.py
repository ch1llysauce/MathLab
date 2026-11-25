"""Unit, API, and security tests for the M5 Computational Visualization Studio."""

from fastapi.testclient import TestClient

from app.main import app
from app.modules.visualization_engine.sampler import generate_visualization_data

client = TestClient(app)


class Test2DVisualization:
    def test_plot_parabola_with_key_points(self):
        res = generate_visualization_data(expression="x^2", x_range=[-5, 5], num_points=101)
        assert res["plot_type"] == "2d"
        assert len(res["traces"][0]["x"]) == 101
        assert len(res["traces"][0]["y"]) == 101

        kinds = {pt["kind"] for pt in res["key_points"]}
        assert "y_intercept" in kinds
        assert "root" in kinds
        assert "local_min" in kinds

    def test_multi_function_derivative_and_tangent_overlays(self):
        res = generate_visualization_data(
            expressions=["x^2 - 4", "2*x"],
            x_range=[-4, 4],
            include_derivative=True,
            include_integral=True,
            tangent_at=1.0,
        )
        names = [t["name"] for t in res["traces"]]
        assert any("Tangent at x=1 (slope=2)" in n for n in names)
        assert any(n.startswith("d/dx:") for n in names)
        assert any(n.startswith("Area under") for n in names)

        roots = [pt["x"] for pt in res["key_points"] if pt["kind"] == "root"]
        assert roots == [-2.0, 2.0]

    def test_parameterized_expression_updates_roots(self):
        res = generate_visualization_data(
            expression="a*x^2 + b",
            x_range=[-5, 5],
            parameters={"a": 2.0, "b": -8.0},
        )
        roots = [pt["x"] for pt in res["key_points"] if pt["kind"] == "root"]
        assert roots == [-2.0, 2.0]

    def test_singularity_produces_none_gaps_without_crashing(self):
        res = generate_visualization_data(
            expression="1/x",
            x_range=[-2, 2],
            num_points=41,  # includes x=0 exact sample
        )
        ys = res["traces"][0]["y"]
        assert None in ys


class Test3DVisualization:
    def test_3d_surface_generation(self):
        res = generate_visualization_data(
            expression="x^2 + y^2",
            plot_type="3d",
            variables=["x", "y"],
            x_range=[-2, 2],
            y_range=[-2, 2],
            grid_size=15,
        )
        assert res["plot_type"] == "3d"
        surface = res["traces"][0]
        assert surface["type"] == "surface"
        assert len(surface["z"]) == 15
        assert len(surface["z"][0]) == 15

    def test_3d_derivative_and_tangent_overlays(self):
        res = generate_visualization_data(
            expressions=["x^2 + y^2", "x*y"],
            plot_type="3d",
            variables=["x", "y"],
            x_range=[-2, 2],
            y_range=[-2, 2],
            grid_size=12,
            include_derivative=True,
            tangent_at=1.0,
            tangent_y=-1.0,
        )
        assert res["plot_type"] == "3d"
        names = [t["name"] for t in res["traces"]]
        assert any(n.startswith("f2(x, y) =") for n in names)
        assert any(n.startswith("∂f/∂x:") for n in names)
        assert any(n.startswith("∂f/∂y:") for n in names)
        assert any("Tangent Plane at (1, -1)" in n for n in names)
        assert any("Tangent ∂x (slope=2)" in n for n in names)
        assert any("Tangent ∂y (slope=-2)" in n for n in names)
        assert any("Tangent Point (1, -1, 2)" in n for n in names)


class TestVisualizationAPIAndSecurity:
    def test_plot_endpoint_2d_and_3d(self):
        resp2d = client.post(
            "/api/v1/visualization/plot",
            json={"expression": "sin(x)", "x_range": [-3.14, 3.14], "num_points": 100},
        )
        assert resp2d.status_code == 200
        assert resp2d.json()["plot_type"] == "2d"

        resp3d = client.post(
            "/api/v1/visualization/plot",
            json={
                "expression": "sin(x)*cos(y)",
                "plot_type": "3d",
                "variables": ["x", "y"],
                "grid_size": 12,
            },
        )
        assert resp3d.status_code == 200
        assert resp3d.json()["plot_type"] == "3d"

    def test_rejects_malicious_expression_and_invalid_bounds(self):
        malicious = client.post(
            "/api/v1/visualization/plot",
            json={"expression": "__import__('os').system('ls')"},
        )
        assert malicious.status_code == 400
        assert malicious.json()["error"]["code"] == "INVALID_EXPRESSION"

        bad_range = client.post(
            "/api/v1/visualization/plot",
            json={"expression": "x^2", "x_range": [5, 1]},
        )
        assert bad_range.status_code == 400
        assert bad_range.json()["error"]["code"] == "INVALID_EXPRESSION"


class TestMatrixVisualization:
    def test_2d_matrix_transform_eigenvectors_and_heatmap(self):
        res = generate_visualization_data(
            plot_type="matrix",
            matrix=[[2, 0], [0, 3]],
            matrix_view="transform",
        )
        assert res["plot_type"] == "2d"
        assert res["metadata"]["equal_aspect"] is True
        names = [t["name"] for t in res["traces"]]
        assert any("A·e₁" in n for n in names)
        assert any("Eigenvector" in n for n in names)

        heat = generate_visualization_data(
            plot_type="matrix",
            matrix=[[1, 2, 3], [4, 5, 6]],
            matrix_view="auto",
        )
        assert heat["plot_type"] == "2d"
        assert heat["traces"][0]["type"] == "heatmap"

    def test_linear_system_plot_finds_intersection(self):
        resp = client.post(
            "/api/v1/visualization/plot",
            json={
                "plot_type": "matrix",
                "matrix": [[2, 1], [1, -1]],
                "vector": [5, 1],
                "matrix_view": "system",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["plot_type"] == "2d"
        assert any(pt["kind"] == "solution" and pt["x"] == 2.0 and pt["y"] == 1.0 for pt in body["key_points"])

    def test_3d_transform_wireframe_4d_projection_and_surface(self):
        t3d = generate_visualization_data(
            plot_type="matrix",
            matrix=[[2, 0, 0], [0, 3, 0], [0, 0, 1]],
            matrix_view="transform",
        )
        assert t3d["plot_type"] == "3d"
        names_3d = [t["name"] for t in t3d["traces"]]
        assert "Unit Cube" in names_3d
        assert any("Transformed Volume (det = 6)" in n for n in names_3d)
        assert any("Eigenvector" in n for n in names_3d)

        proj_4d = generate_visualization_data(
            plot_type="matrix",
            matrix=[[1, 0, 0, 2], [0, 1, 0, 3], [0, 0, 1, 4], [0, 0, 0, 1]],
            matrix_view="transform",
        )
        assert proj_4d["plot_type"] == "3d"
        assert proj_4d["metadata"]["projected_from_dim"] == 4

        surf = generate_visualization_data(
            plot_type="matrix",
            matrix=[[1, 2, 3, 4], [2, 4, 3, 1], [0, 1, 2, 3], [4, 3, 2, 1]],
            matrix_view="surface",
        )
        assert surf["plot_type"] == "3d"
        assert surf["traces"][0]["type"] == "surface"
