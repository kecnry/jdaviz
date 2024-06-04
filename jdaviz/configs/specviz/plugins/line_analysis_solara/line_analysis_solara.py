import solara
from jdaviz.core.registries import tray_registry
from jdaviz.core.user_api import PluginUserApi


__all__ = ['LineAnalysisSolara']


@solara.component
def PluginUI(state):
    solara.SliderInt("Word limit", value=state._word_limit, min=2, max=20)
    solara.InputText(label="Your sentence", value=state._sentence, continuous_update=True)

    solara.Button("do something", on_click=state.increment_word_limit)

    status, message = state.message
    getattr(solara, status, solara.Warning)(message)



@tray_registry('solara-line-analysis', label="Line Analysis (Solara)", viewer_requirements='spectrum')
class LineAnalysisSolara():

    def __init__(self, app=None, tray_instance=False):
        self._sentence = solara.reactive("Solara makes our team more productive")
        self._word_limit = solara.reactive(10)  

        self._widget = PluginUI.widget(state=self)

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('sentence', 'increment_word_limit'),
                             readonly=('word_limit', 'message'))

    @property
    def message(self):
        # Calculate word_count within the component to ensure re-execution when reactive variables change.
        word_count = len(self.sentence.split())

        # Display messages based on the current word count and word limit.
        if word_count >= int(self.word_limit):
            return "Error", f"With {word_count} words, you passed the word limit of {self.word_limit}."
        elif word_count >= int(0.8 * self.word_limit):
            return "Warning", f"With {word_count} words, you are close to the word limit of {self.word_limit}."
        else:
            return "Success", "Great short writing!"

    @property
    def word_limit(self):
        return self._word_limit.value

    @property
    def sentence(self):
        return self._sentence.value

    @sentence.setter
    def sentence(self, value):
        self._sentence.value = value

    def increment_word_limit(self, *args):
        self._word_limit.value += 1
        return self._word_limit.value
