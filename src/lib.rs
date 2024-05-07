#![allow(dead_code)]

extern crate chrono;
extern crate chrono_tz;
extern crate pyo3;
extern crate rust_decimal;
extern crate serde;
extern crate serde_json;

use chrono::offset::LocalResult;
use chrono::Datelike;
use chrono::Timelike;
use pyo3::exceptions::*;
use pyo3::prelude::*;
use pyo3::types::*;

use chrono::{NaiveDate, NaiveDateTime, NaiveTime, TimeZone};
use chrono_tz::Tz;
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};

// For now, we serialize schemas as JSON, maybe in the future we can use:
// https://crates.io/crates/pythonize
#[derive(Debug, Deserialize, Serialize)]
#[serde(tag = "kind")]
enum Field {
    #[serde(rename = "STR")]
    String(StrField),
    #[serde(rename = "INT")]
    Int(IntField),
    #[serde(rename = "FLOAT")]
    Float(FloatField),
    #[serde(rename = "DECIMAL")]
    Decimal(DecimalField),
    #[serde(rename = "BOOL")]
    Bool(BoolField),
    #[serde(rename = "ENUM")]
    Enum(EnumField),
    #[serde(rename = "DATETIME")]
    Datetime(DatetimeField),
    #[serde(rename = "DATE")]
    Date(DateField),
    #[serde(rename = "TIME")]
    Time(TimeField),
}

#[derive(Debug, Deserialize, Serialize)]
struct StrField {
    required: bool,
    min_length: Option<i32>,
    max_length: Option<i32>,
    invalid_characters: Option<String>,
}

#[derive(Debug, Deserialize, Serialize)]
struct IntField {
    required: bool,
    min_value: Option<i32>,
    max_value: Option<i32>,
}

#[derive(Debug, Deserialize, Serialize)]
struct FloatField {
    required: bool,
    min_value: Option<f64>,
    max_value: Option<f64>,
}

#[derive(Debug, Deserialize, Serialize)]
struct DecimalField {
    required: bool,
    max_decimal_places: Option<i32>,
    min_value: Option<Decimal>, // Note this is String
    max_value: Option<Decimal>, // Note this is String
}

#[derive(Debug, Deserialize, Serialize)]
struct BoolField {
    required: bool,
    true_value: String,  // Renamed true to true_value as true is a keyword
    false_value: String, // Renamed false to false_value as false is a keyword
}

#[derive(Debug, Deserialize, Serialize)]
struct EnumField {
    required: bool,
    values: Vec<String>,
}

#[derive(Debug, Deserialize, Serialize)]
struct DatetimeField {
    required: bool,
    format: String,
    time_zone: String,
}

#[derive(Debug, Deserialize, Serialize)]
struct DateField {
    required: bool,
    format: String,
}

#[derive(Debug, Deserialize, Serialize)]
struct TimeField {
    required: bool,
    format: String,
}

#[derive(Debug, Deserialize, Serialize)]
struct Line {
    name: String,
    fields: Vec<Field>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct Schema {
    delimiter: String,
    quote: Option<String>,
    trailing_delimiter: bool,
    lines: Vec<Line>,
}

#[pyclass(frozen, module = "xlineparse")]
pub struct Parser {
    // Schema lives for the duration of the program
    pub schema: &'static Schema,
}
#[pymethods]
impl Parser {
    #[new]
    fn new<'a>(_py: Python<'a>, schema_json_str: &str) -> PyResult<Self> {
        let parsed_data: serde_json::Result<Schema> = serde_json::from_str(schema_json_str);
        match parsed_data {
            Ok(schemas) => {
                // Schemas live for the duration of the program
                let boxed = Box::new(schemas);
                let leaked = Box::leak(boxed);
                Ok(Parser { schema: leaked })
            }
            Err(e) => Err(PyValueError::new_err(e.to_string())),
        }
    }
    fn parse_line<'a>(&self, _py: Python<'a>, line: &str) -> PyResult<PyObject> {
        if self.schema.delimiter.len() != 1 {
            return Err(PyValueError::new_err("Delimiter needs to be of length 1"));
        }
        let delimiter = self.schema.delimiter.chars().next().unwrap();

        let mut line_stripped = line.trim_end_matches('\n');
        if self.schema.trailing_delimiter {
            if !line_stripped.ends_with(delimiter) {
                return Err(PyValueError::new_err(
                    "Line doesn't have trailing delimiter",
                ));
            }
            line_stripped = line.trim_end_matches(delimiter);
        }

        let mut parts = line_stripped.split(delimiter);
        let or_first = parts.next();
        if or_first.is_none() {
            return Err(PyValueError::new_err("Split line has length < 1"));
        }
        let first = or_first.unwrap();
        let rest: Vec<&str> = parts.collect();

        let or_schema_line = self
            .schema
            .lines
            .iter()
            .filter(|schema_line| schema_line.name == first)
            .next();
        if or_schema_line.is_none() {
            return Err(PyValueError::new_err(format!(
                "No schema line matching {}",
                first
            )));
        }
        let schema_line = or_schema_line.unwrap();
        if schema_line.fields.len() != rest.len() {
            return Err(PyValueError::new_err(format!(
                "Mismatched line length, schema length: {}, actual length: {} + 1",
                schema_line.fields.len(),
                rest.len()
            )));
        }

        let mut py_items: Vec<PyObject> = vec![first.into_py(_py)];
        for (schema_field, &part) in schema_line.fields.iter().zip(rest.iter()) {
            py_items.push(part_to_py(_py, schema_field, part)?)
        }
        Ok(PyTuple::new(_py, &py_items).into_py(_py))
    }
}

fn part_to_py<'a>(_py: Python<'a>, schema_field: &Field, part: &str) -> PyResult<PyObject> {
    let none: Option<&str> = None;
    let err: PyResult<PyObject> = Err(PyValueError::new_err(format!(
        "Unable to parse {} as {:?}",
        part, schema_field
    )));
    match (part, schema_field) {
        (
            "",
            Field::String(StrField {
                required: false, ..
            })
            | Field::Int(IntField {
                required: false, ..
            })
            | Field::Float(FloatField {
                required: false, ..
            })
            | Field::Decimal(DecimalField {
                required: false, ..
            })
            | Field::Bool(BoolField {
                required: false, ..
            })
            | Field::Enum(EnumField {
                required: false, ..
            })
            | Field::Datetime(DatetimeField {
                required: false, ..
            })
            | Field::Date(DateField {
                required: false, ..
            })
            | Field::Time(TimeField {
                required: false, ..
            }),
        ) => Ok(none.into_py(_py)),
        (_, Field::String(_)) => Ok(String::from(part).into_py(_py)),
        (_, Field::Int(_)) => part
            .parse::<i64>()
            .map_or_else(|_| err, |i| Ok(i.into_py(_py))),
        (_, Field::Float(_)) => part
            .parse::<f64>()
            .map_or_else(|_| err, |i| Ok(i.into_py(_py))),
        (_, Field::Decimal(_)) => {
            Decimal::from_str_exact(part).map_or_else(|_| err, |i| Ok(i.into_py(_py)))
        }
        (
            _,
            Field::Bool(BoolField {
                true_value,
                false_value,
                ..
            }),
        ) => {
            if part == true_value {
                Ok(true.into_py(_py))
            } else if part == false_value {
                Ok(false.into_py(_py))
            } else {
                err
            }
        }
        // TODO: Enum
        (
            _,
            Field::Datetime(DatetimeField {
                format, time_zone, ..
            }),
        ) => {
            let tz: Result<Tz, _> = time_zone.parse();
            if tz.is_err() {
                return Err(PyValueError::new_err(format!(
                    "Invalid time zone: {}",
                    time_zone
                )));
            }
            NaiveDateTime::parse_from_str(part, format).map_or_else(
                |_| err,
                |i| {
                    let dt = tz.unwrap().with_ymd_and_hms(
                        i.year(),
                        i.month(),
                        i.day(),
                        i.hour(),
                        i.minute(),
                        i.second(),
                    );
                    match dt {
                        LocalResult::Single(dt) => Ok(dt.into_py(_py)),
                        _ => Err(PyValueError::new_err(format!("Invalid datetime: {}", part))),
                    }
                },
            )
        }
        (_, Field::Date(DateField { format, .. })) => {
            NaiveDate::parse_from_str(part, format).map_or_else(|_| err, |i| Ok(i.into_py(_py)))
        }
        (_, Field::Time(TimeField { format, .. })) => {
            NaiveTime::parse_from_str(part, format).map_or_else(|_| err, |i| Ok(i.into_py(_py)))
        }
        _ => err,
    }
}

#[pymodule]
#[pyo3(name = "xlineparse")]
fn init_mod(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Parser>()?;
    Ok(())
}
