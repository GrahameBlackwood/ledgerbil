class LdgException(Exception):
    def __init__(self, value):
        self.value = value


class LdgScheduleFileConfigError(LdgException):
    pass


class LdgScheduleThingParametersError(LdgException):
    pass


class LdgScheduleThingLabelError(LdgException):
    pass


class LdgScheduleUnrecognizedIntervalUom(LdgException):
    pass


class LdgReconcilerMoreThanOneMatchingAccount(LdgException):
    pass


class LdgReconcilerMultipleStatuses(LdgException):
    pass


class LdgReconcilerUnhandledSharesScenario(LdgException):
    pass
