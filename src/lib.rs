#![allow(dead_code)]

extern crate pyo3;

use pyo3::prelude::*;

#[pymodule]
#[pyo3(name = "xlineparse")]
fn init_mod(_py: Python, m: &PyModule) -> PyResult<()> {
    #[pyfn(m)]
    #[pyo3(name = "foo")]
    fn foo<'a>(
        _py: Python<'a>,
    ) -> PyResult<String> {
        Ok(String::from("hullo"))
    }

    Ok(())
}
