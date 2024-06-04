import solara
from jdaviz.core.registries import tray_registry
from jdaviz.core.user_api import PluginUserApi


__all__ = ['LineAnalysisSolara']


@solara.component
def PluginUI(state):
    solara.SliderInt("Word limit", value=state.word_limit, min=2, max=20)
    # UI-only logic (anything that does not need to be exposed via the API) can be done in-line
    if state.word_limit.value > 20:
        solara.Error("Word limit can only be up to 20")

    solara.InputText(label="Your sentence", value=state.sentence, continuous_update=True)
    solara.Button("Increase Word Limit", on_click=state.increment_word_limit)

    # Logic that should also be exposed to the API should live in methods/properties in the plugin
    # which should then only be *rendered* in the UI
    status, message = state.message
    getattr(solara, status, solara.Warning)(message)


@tray_registry('solara-line-analysis', label="Line Analysis (Solara)", viewer_requirements='spectrum')
class LineAnalysisSolara():

    def __init__(self, app=None, tray_instance=False):
        # internally these are reactive state objects, so setting/getting value require .value
        # the user_api then maps all getattr and setattr so that the reactive object is abstracted away
        self.sentence = solara.reactive("Solara makes our team more productive")
        self.word_limit = solara.reactive(10)  

        self._widget = PluginUI.widget(state=self)

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('sentence', 'word_limit', 'increment_word_limit'),
                             readonly=('message',))

    @property
    def message(self):
        # Calculate word_count within the component to ensure re-execution when reactive variables change.
        word_count = len(self.sentence.value.split())
        word_limit = self.word_limit.value

        # Display messages based on the current word count and word limit.
        if word_count >= int(word_limit):
            return "Error", f"With {word_count} words, you passed the word limit of {word_limit}."
        elif word_count >= int(0.8 * word_limit):
            return "Warning", f"With {word_count} words, you are close to the word limit of {word_limit}."
        else:
            return "Success", "Great short writing!"

    def increment_word_limit(self, *args):
        self.word_limit.value += 1
        return self.word_limit.value
