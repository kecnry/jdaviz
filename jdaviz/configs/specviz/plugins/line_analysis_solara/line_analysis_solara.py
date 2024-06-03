import solara
from jdaviz.core.registries import tray_registry
from jdaviz.core.user_api import PluginUserApi


__all__ = ['LineAnalysisSolara', 'LineAnalysisSolaraPlugin']

# because these are defined here, they're shared across any and all instances
sentence = solara.reactive("Solara makes our team more productive")
word_limit = solara.reactive(10)

@solara.component
def LineAnalysisSolara():
    # Calculate word_count within the component to ensure re-execution when reactive variables change.
    word_count = len(sentence.value.split())

    solara.SliderInt("Word limit", value=word_limit, min=2, max=20)
    solara.InputText(label="Your sentence", value=sentence, continuous_update=True)

    # Display messages based on the current word count and word limit.
    if word_count >= int(word_limit.value):
        solara.Error(f"With {word_count} words, you passed the word limit of {word_limit.value}.")
    elif word_count >= int(0.8 * word_limit.value):
        solara.Warning(f"With {word_count} words, you are close to the word limit of {word_limit.value}.")
    else:
        solara.Success("Great short writing!")



_internal_attrs = ('_plg', '_widget', 'user_api')

@tray_registry('solara-line-analysis', label="Line Analysis (Solara)", viewer_requirements='spectrum')
class LineAnalysisSolaraPlugin():
    def __init__(self, app=None, tray_instance=False):
        self._plg = LineAnalysisSolara
        self._widget = self._plg.widget()

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('sentence', 'word_limit'),
                             readonly=('word_limit',))

    @property
    def word_limit(self):
        return word_limit.value

    @property
    def sentence(self):
        return sentence.value

    @sentence.setter
    def sentence(self, value):
        sentence.value = value

    def __getattr__(self, attr):
        if attr in _internal_attrs:
            return super().__getattribute__(attr)

        return getattr(self._widget, attr)

#    def __setattr__(self, attr, value):
#        if attr in _internal_attrs:
#            return super().__setattr__(attr, value)
#        setattr(self._widget, attr, value)
