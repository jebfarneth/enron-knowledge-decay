from enron_importance.figures.funnel import STEPS, draw
from enron_importance.figures.style import save


def test_funnel_figure_renders_every_step(tmp_path):
    funnel = {key: 1000 - i * 100 for i, (key, _) in enumerate(STEPS)}
    fig = draw(funnel)
    labels = [t.get_text() for t in fig.axes[0].get_yticklabels()]
    assert labels == [label for _, label in STEPS]
    written = save(fig, tmp_path, "fig")
    assert [p.suffix for p in written] == [".pdf", ".png"] and all(p.stat().st_size > 0 for p in written)


def test_baselines_figure_orders_measures_by_accuracy(tmp_path):
    import pandas as pd
    from enron_importance.figures.baselines import draw as draw_baselines
    table = pd.DataFrame({"measure": ["degree", "pagerank", "out_strength"], "accuracy": [0.65, 0.61, 0.52],
                          "ci_low": [0.57, 0.53, 0.44], "ci_high": [0.72, 0.69, 0.60]})
    fig = draw_baselines(table)
    labels = [t.get_text() for t in fig.axes[0].get_yticklabels()]
    assert labels[-1] == "Degree (distinct contacts)" and labels[0] == "Email sent (weighted)"
    save(fig, tmp_path, "baselines")
