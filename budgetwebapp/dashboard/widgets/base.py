from abc import ABC, abstractmethod


class BaseWidgetLogic(ABC):
    def __init__(self, widget):
        self.widget = widget

    # ---------- CONFIG ----------
    def get_config(self):
        schema = self.widget.get_definition().config_schema
        if not schema:
            return self.widget.config or {}
        return schema(**(self.widget.config or {}))

    # ---------- STATE ----------
    def get_state(self):
        schema = self.widget.get_definition().state_schema
        if not schema:
            return self.widget.state or {}
        return schema(**(self.widget.state or {}))

    # ---------- OUTPUT ----------
    def validate_output(self, data):
        schema = self.widget.get_definition().output_schema
        if not schema:
            return data
        return schema(**data).model_dump()

    # ---------- PIPELINE ----------
    def run(self, filters=None):
        config = self.get_config()
        state = self.get_state()

        data = self.update_data(config, state, filters)
        return self.validate_output(data)

    # ---------- UI (STATIC FROM DEFINITION) ----------
    def get_ui_schema(self):
        return self.widget.get_definition().ui_schema or {
            "controls": {},
            "meta": {
                "type": self.widget.widget_type,
                "subtype": self.widget.subtype,
            },
        }

    # ---------- RUNTIME EXTENSION ----------
    def get_runtime_options(self, filters=None):
        return None

    @abstractmethod
    def update_data(self, config, state, filters=None):
        pass