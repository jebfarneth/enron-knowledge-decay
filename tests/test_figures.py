from enron_importance.figures.funnel import STEPS, draw
from enron_importance.figures.style import save


def test_funnel_figure_renders_every_step(tmp_path):
    funnel = {key: 1000 - i * 100 for i, (key, _) in enumerate(STEPS)}
    fig = draw(funnel)
    labels = [t.get_text() for t in fig.axes[0].get_yticklabels()]
    assert labels == [label for _, label in STEPS]
    written = save(fig, tmp_path, "fig")
    assert [p.suffix for p in written] == [".pdf", ".png"] and all(p.stat().st_size > 0 for p in written)
