import solara
from jdaviz.core.registries import tray_registry
from jdaviz.core.user_api import PluginUserApi


__all__ = ['LineAnalysisSolara', 'LineAnalysisSolaraPlugin']


@solara.component
def LineAnalysisSolara(sentence, word_limit, do_something):
    # Calculate word_count within the component to ensure re-execution when reactive variables change.
    word_count = len(sentence.value.split())

    solara.SliderInt("Word limit", value=word_limit, min=2, max=20)
    solara.InputText(label="Your sentence", value=sentence, continuous_update=True)

    solara.Button("do something", on_click=do_something)

    # Display messages based on the current word count and word limit.
    if word_count >= int(word_limit.value):
        solara.Error(f"With {word_count} words, you passed the word limit of {word_limit.value}.")
    elif word_count >= int(0.8 * word_limit.value):
        solara.Warning(f"With {word_count} words, you are close to the word limit of {word_limit.value}.")
    else:
        solara.Success("Great short writing!")


@tray_registry('solara-line-analysis', label="Line Analysis (Solara)", viewer_requirements='spectrum')
class LineAnalysisSolaraPlugin():

    def __init__(self, app=None, tray_instance=False):
        self._sentence = solara.reactive("Solara makes our team more productive")
        self._word_limit = solara.reactive(10)  

        self._widget = LineAnalysisSolara.widget(sentence=self._sentence, word_limit=self._word_limit,
                                                 do_something=self.do_something)

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('sentence', 'word_limit', 'do_something'),
                             readonly=('word_limit',))

    @property
    def word_limit(self):
        return self._word_limit.value

    @property
    def sentence(self):
        return self._sentence.value

    @sentence.setter
    def sentence(self, value):
        self._sentence.value = value

    def do_something(self, *args):
        self._word_limit.value += 1
