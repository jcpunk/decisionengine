import pandas as pd

from decisionengine.framework.modules import Source
from decisionengine.framework.modules.Source import Parameter


@Source.supports_config(Parameter('multiplier', type=int))
@Source.produces(foo=pd.DataFrame)
class SourceWithSampleConfigNOP(Source.Source):

    def __init__(self, config):
        super().__init__(config)
        self.multiplier = config.get('multiplier')

    def acquire(self):
        return {'foo': pd.DataFrame([
            {'col1': 'value1', 'col2': 0.5 * self.multiplier},
            {'col1': 'value2', 'col2': 2.0 * self.multiplier},
        ])}


Source.describe(SourceWithSampleConfigNOP, sample_config={'multiplier': 1})
