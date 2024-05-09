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
    Str(StrField),
    #[serde(rename = "STR_ENUM")]
    StrEnum(StrEnumField),
    #[serde(rename = "INT")]
    Int(IntField),
    #[serde(rename = "INT_ENUM")]
    IntEnum(IntEnumField),
    #[serde(rename = "FLOAT")]
    Float(FloatField),
    #[serde(rename = "DECIMAL")]
    Decimal(DecimalField),
    #[serde(rename = "BOOL")]
    Bool(BoolField),
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
    min_length: Option<usize>,
    max_length: Option<usize>,
    invalid_characters: Option<String>,
}

#[derive(Debug, Deserialize, Serialize)]
struct StrEnumField {
    required: bool,
    values: Vec<String>,
}

#[derive(Debug, Deserialize, Serialize)]
struct IntField {
    required: bool,
    // We use f64 here so we can represent large numbers, bit naughty
    min_value: Option<f64>,
    max_value: Option<f64>,
}

#[derive(Debug, Deserialize, Serialize)]
struct IntEnumField {
    required: bool,
    values: Vec<i64>,
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
    round_decimal_places: Option<u32>,
    min_value: Option<Decimal>,
    max_value: Option<Decimal>,
}

#[derive(Debug, Deserialize, Serialize)]
struct BoolField {
    required: bool,
    true_value: String,
    false_value: Option<String>,
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
    quote_str: Option<String>,
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
                // Schema lives for the duration of the program
                let boxed = Box::new(schemas);
                let leaked = Box::leak(boxed);
                Ok(Parser { schema: leaked })
            }
            Err(e) => Err(PyValueError::new_err(e.to_string())),
        }
    }
    fn parse_line<'a>(&self, _py: Python<'a>, line: &str) -> PyResult<PyObject> {
        let delimiter = if self.schema.delimiter.len() == 1 {
            Ok(self.schema.delimiter.chars().next().unwrap())
        } else {
            Err(PyValueError::new_err("Delimiter needs to be of length 1"))
        }?;

        let quote_char = if let Some(quote_str) = &self.schema.quote_str {
            if quote_str.len() == 1 {
                Ok(Some(quote_str.chars().next().unwrap()))
            } else {
                Err(PyValueError::new_err("Quote needs to be of length 1"))
            }?
        } else {
            None
        };

        let mut line_stripped = line.trim_end_matches('\n');
        if self.schema.trailing_delimiter {
            line_stripped = if line_stripped.ends_with(delimiter) {
                Ok(&line_stripped[..line_stripped.len() - 1])
            } else {
                Err(PyValueError::new_err(
                    "Line doesn't have trailing delimiter",
                ))
            }?;
        };
        let split = split_line(line_stripped, delimiter, quote_char);
        let parts: Vec<&str> = split.iter().map(|s| s.as_str()).collect();

        let first = *parts
            .get(0)
            .ok_or(PyValueError::new_err("Split line has length < 1"))?;

        let schema_line = self
            .schema
            .lines
            .iter()
            .find(|schema_line| schema_line.name == first)
            .ok_or_else(|| PyValueError::new_err(format!("No schema line matching '{}'", first)))?;

        if schema_line.fields.len() != parts.len() - 1 {
            return Err(PyValueError::new_err(format!(
                "Mismatched line length, schema length: {}, actual length: (header=1) + {}",
                schema_line.fields.len(),
                parts.len() - 1
            )));
        }

        let mut py_items: Vec<PyObject> = vec![first.into_py(_py)];
        for (schema_field, &part) in schema_line.fields.iter().zip(parts.iter().skip(1)) {
            py_items.push(part_to_py(_py, quote_char, schema_field, part)?)
        }
        Ok(PyTuple::new(_py, &py_items).into_py(_py))
    }
}

fn split_line(line: &str, delimiter: char, quote_char: Option<char>) -> Vec<String> {
    let mut parts_mut: Vec<String> = vec![];
    let mut current_part = String::new();
    let mut in_quoted = false;
    for ch in line.chars() {
        if quote_char.is_some() && ch == quote_char.unwrap() {
            in_quoted = !in_quoted;
        } else if ch == delimiter && !in_quoted {
            parts_mut.push(current_part.clone());
            current_part.clear();
        } else {
            current_part.push(ch);
        };
    }
    parts_mut.push(current_part.clone());
    parts_mut
}

fn required(field: &Field) -> bool {
    match field {
        Field::Str(StrField { required, .. })
        | Field::StrEnum(StrEnumField { required, .. })
        | Field::Int(IntField { required, .. })
        | Field::IntEnum(IntEnumField { required, .. })
        | Field::Float(FloatField { required, .. })
        | Field::Decimal(DecimalField { required, .. })
        | Field::Bool(BoolField { required, .. })
        | Field::Datetime(DatetimeField { required, .. })
        | Field::Date(DateField { required, .. })
        | Field::Time(TimeField { required, .. }) => *required,
    }
}

fn part_to_py<'a>(
    _py: Python<'a>,
    quote_char: Option<char>,
    schema_field: &Field,
    part: &str,
) -> PyResult<PyObject> {
    let none: Option<&str> = None;
    let err = |extra: &str| {
        Err(PyValueError::new_err(format!(
            "{} - '{}' given schema: {:?}",
            extra, part, schema_field,
        )))
    };

    if part == "" && !required(schema_field) {
        return Ok(none.into_py(_py));
    }

    // We allow 'A' to pass as the enum or bool '"A"'
    let mut part_with_quotes = part;
    let mut _s = String::new();
    quote_char.map(|q| {
        _s.push(q);
        _s.push_str(part);
        _s.push(q);
        part_with_quotes = _s.as_str();
    });

    match schema_field {
        Field::Str(StrField {
            min_length,
            max_length,
            invalid_characters,
            ..
        }) => {
            if min_length.is_some() && part.len() < min_length.unwrap() {
                return err("String is too short");
            }
            if max_length.is_some() && part.len() > max_length.unwrap() {
                return err("String is too long");
            }
            if let Some(invalid_characters_) = invalid_characters {
                if part.chars().any(|c| invalid_characters_.contains(c)) {
                    return err("String contains invalid characters");
                }
            }
            Ok(String::from(part).into_py(_py))
        }
        Field::StrEnum(StrEnumField { values, .. }) => {
            if values.contains(&String::from(part)) {
                Ok(String::from(part).into_py(_py))
            } else if values.contains(&String::from(part_with_quotes)) {
                Ok(String::from(part_with_quotes).into_py(_py))
            } else {
                err("Value not in enum")
            }
        }
        Field::Int(IntField {
            min_value,
            max_value,
            ..
        }) => part.parse::<i128>().map_or_else(
            |_| err("Does not parse as int"),
            |i| {
                if min_value.is_some() && i < (min_value.unwrap() as i128) {
                    return err("Int is too small");
                }
                if max_value.is_some() && i > (max_value.unwrap() as i128) {
                    return err("Int is too large");
                }
                Ok(i.into_py(_py))
            },
        ),
        Field::IntEnum(IntEnumField { values, .. }) => part.parse::<i64>().map_or_else(
            |_| err("Does not parse as int"),
            |i| {
                if values.contains(&i) {
                    Ok(i.into_py(_py))
                } else {
                    err("Value not in enum")
                }
            },
        ),
        Field::Float(FloatField {
            min_value,
            max_value,
            ..
        }) => part.parse::<f64>().map_or_else(
            |_| err("Does not parse as float"),
            |i| {
                if min_value.is_some() && i < min_value.unwrap() {
                    return err("Float is too small");
                }
                if max_value.is_some() && i > max_value.unwrap() {
                    return err("Float is too large");
                }
                Ok(i.into_py(_py))
            },
        ),
        Field::Decimal(DecimalField {
            round_decimal_places,
            min_value,
            max_value,
            ..
        }) => Decimal::from_str_exact(part).map_or_else(
            |_| err("Does not parse as decimal"),
            |i| {
                if min_value.is_some() && i < min_value.unwrap() {
                    return err("Decimal is too small");
                }
                if max_value.is_some() && i > max_value.unwrap() {
                    return err("Decimal is too large");
                }
                if round_decimal_places.is_some() {
                    return Ok(i.round_dp(round_decimal_places.unwrap()).into_py(_py));
                }
                Ok(i.into_py(_py))
            },
        ),
        Field::Bool(BoolField {
            true_value,
            false_value,
            ..
        }) => {
            if part == true_value || part_with_quotes == true_value {
                Ok(true.into_py(_py))
            } else if false_value.as_ref().map_or(false, |false_value_| {
                part == false_value_ || part_with_quotes == false_value_
            }) {
                Ok(false.into_py(_py))
            } else {
                err("Value is neither true or false value")
            }
        }
        Field::Datetime(DatetimeField {
            format, time_zone, ..
        }) => {
            let tz: Result<Tz, _> = time_zone.parse();
            if tz.is_err() {
                return err("Invalid timezone");
            }
            NaiveDateTime::parse_from_str(part, format).map_or_else(
                |_| err("Does not parse as datetime"),
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
                        _ => err("Does not parse as datetime"),
                    }
                },
            )
        }
        Field::Date(DateField { format, .. }) => NaiveDate::parse_from_str(part, format)
            .map_or_else(|_| err("Does not parse as date"), |i| Ok(i.into_py(_py))),
        Field::Time(TimeField { format, .. }) => {
            let part_24_to_00 = if part == "240000" { "000000" } else { part }; // I kno rite
            NaiveTime::parse_from_str(part_24_to_00, format)
                .map_or_else(|_| err("Does not parse as time"), |i| Ok(i.into_py(_py)))
        }
    }
}

#[pymodule]
#[pyo3(name = "xlineparse")]
fn init_mod(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Parser>()?;
    Ok(())
}
