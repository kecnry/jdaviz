import solara
from jdaviz.core.registries import tray_registry
from jdaviz.core.user_api import PluginUserApi


__all__ = ['LineAnalysisSolara']

# separate state
class PluginState:
    def __init__(self, *args, **kwargs):
        self.sentence = solara.reactive("Solara makes our team more productive")
        self.word_limit = solara.reactive(10)  


@solara.component
def PluginUI(state, plugin):
    # Calculate word_count within the component to ensure re-execution when reactive variables change.
    word_count = len(state.sentence.value.split())

    solara.SliderInt("Word limit", value=state.word_limit, min=2, max=20)
    solara.InputText(label="Your sentence", value=state.sentence, continuous_update=True)

    solara.Button("do something", on_click=plugin.increment_word_limit)

    # Display messages based on the current word count and word limit.
    if word_count >= int(state.word_limit.value):
        solara.Error(f"With {word_count} words, you passed the word limit of {state.word_limit.value}.")
    elif word_count >= int(0.8 * state.word_limit.value):
        solara.Warning(f"With {word_count} words, you are close to the word limit of {state.word_limit.value}.")
    else:
        solara.Success("Great short writing!")


@tray_registry('solara-line-analysis', label="Line Analysis (Solara)", viewer_requirements='spectrum')
class LineAnalysisSolara():

    def __init__(self, app=None, tray_instance=False):
        self._state = PluginState()
        self._widget = PluginUI.widget(state=self._state, plugin=self)

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('sentence', 'word_limit', 'increment_word_limit'),
                             readonly=('word_limit',))

    @property
    def word_limit(self):
        return self._state.word_limit.value

    @property
    def sentence(self):
        return self._state.sentence.value

    @sentence.setter
    def sentence(self, value):
        self._state.sentence.value = value

    def increment_word_limit(self, *args):
        self._state.word_limit.value += 1
        return self._state.word_limit.value
