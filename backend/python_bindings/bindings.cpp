#include <pybind11/pybind11.h>

namespace py = pybind11;

PYBIND11_MODULE(fm_native, m) {
    m.doc() = "Football Manager native backend scaffold";
    m.def("backend_status", []() {
        return "native-backend-scaffold";
    });
}
