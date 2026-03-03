import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import plotly.express as px

# --- 1. إعداد قاعدة البيانات ---
Base = declarative_base()
engine = create_engine('sqlite:///erp_complete_v4.db')
Session = sessionmaker(bind=engine)
session = Session()


class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    price = Column(Float)
    stock = Column(Integer)


class Customer(Base):
    __tablename__ = 'customers'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    phone = Column(String)


class Sale(Base):
    __tablename__ = 'sales'
    id = Column(Integer, primary_key=True)
    customer_name = Column(String)
    product_name = Column(String)
    quantity = Column(Integer)
    total = Column(Float)
    date = Column(DateTime, default=datetime.datetime.now)


class Purchase(Base):
    __tablename__ = 'purchases'
    id = Column(Integer, primary_key=True)
    item_name = Column(String)
    qty = Column(Integer)
    cost = Column(Float)
    date = Column(DateTime, default=datetime.datetime.now)


class Finance(Base):
    __tablename__ = 'finance'
    id = Column(Integer, primary_key=True)
    type = Column(String)  # رواتب، فواتير، إلخ
    amount = Column(Float)
    note = Column(String)


Base.metadata.create_all(engine)

# --- 2. واجهة التطبيق ---
st.set_page_config(page_title="نظام ERP المتكامل", layout="wide")

st.sidebar.title("🛠️ لوحة التحكم")
menu = ["📊 الرئيسية", "📦 المخزن", "🛒 المشتريات", "💰 المبيعات", "👥 العملاء", "🧾 الرواتب والمالية"]
choice = st.sidebar.selectbox("اختر القسم", menu)


# --- وظائف مساعدة للحذف ---
def delete_item(model, item_id):
    item = session.query(model).get(item_id)
    session.delete(item)
    session.commit()
    st.rerun()


# --- 📊 القسم: الرئيسية ---
if choice == "📊 الرئيسية":
    st.title("📈 ملخص الأداء العام")
    s_total = sum([s.total for s in session.query(Sale).all()])
    p_total = sum([p.cost for p in session.query(Purchase).all()])
    f_total = sum([f.amount for f in session.query(Finance).all()])

    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي المبيعات", f"{s_total} $")
    c2.metric("إجمالي المصاريف (مشتريات + مالية)", f"{p_total + f_total} $")
    c3.metric("صافي الربح", f"{s_total - (p_total + f_total)} $")

# --- 📦 القسم: المخزن ---
elif choice == "📦 المخزن":
    st.title("📦 إدارة المخزون")
    with st.expander("📝 إضافة/تعديل منتج"):
        name = st.text_input("اسم المنتج")
        price = st.number_input("سعر البيع", min_value=0.0)
        stock = st.number_input("الكمية الحالية", min_value=0)
        if st.button("حفظ في المخزن"):
            session.add(Product(name=name, price=price, stock=stock))
            session.commit()
            st.success("تم الحفظ")

    items = session.query(Product).all()
    for i in items:
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        col1.write(f"**{i.name}**")
        col2.write(f"السعر: {i.price}$")
        col3.write(f"المخزون: {i.stock}")
        if col4.button("🗑️", key=f"del_p_{i.id}"):
            delete_item(Product, i.id)

# --- 🛒 القسم: المشتريات ---
elif choice == "🛒 المشتريات":
    st.title("🛒 إدارة المشتريات")
    with st.form("buy_form"):
        item = st.text_input("اسم المادة المشتراة")
        q = st.number_input("الكمية", min_value=1)
        c = st.number_input("التكلفة الإجمالية", min_value=0.0)
        if st.form_submit_button("تسجيل شراء"):
            session.add(Purchase(item_name=item, qty=q, cost=c))
            # تحديث المخزن تلقائياً إذا كان المنتج موجوداً
            prod = session.query(Product).filter_by(name=item).first()
            if prod: prod.stock += q
            session.commit()
            st.success("تم تسجيل المشتريات وتحديث المخزن")

    purchases = session.query(Purchase).all()
    st.table(pd.DataFrame([(p.id, p.item_name, p.qty, p.cost, p.date) for p in purchases], columns=["ID", "المادة", "الكمية", "التكلفة", "التاريخ"]))

# --- 💰 القسم: المبيعات ---
elif choice == "💰 المبيعات":
    st.title("💰 نظام المبيعات والفواتير")
    prods = session.query(Product).all()
    custs = session.query(Customer).all()

    with st.container(border=True):
        c_name = st.selectbox("اختر العميل", [c.name for c in custs]) if custs else st.text_input("اسم العميل")
        p_obj = st.selectbox("اخter المنتج", prods, format_func=lambda x: f"{x.name} (المتوفر: {x.stock})")
        qty = st.number_input("الكمية المطلوبة", min_value=1)

        if st.button("إصدار فاتورة وبيع"):
            if p_obj.stock >= qty:
                total_val = p_obj.price * qty
                session.add(Sale(customer_name=c_name, product_name=p_obj.name, quantity=qty, total=total_val))
                p_obj.stock -= qty
                session.commit()

                # شكل الفاتورة
                st.markdown(f"""
                <div style="border:2px solid #eee; padding:20px; border-radius:10px">
                    <h3>📄 فاتورة مبيعات</h3>
                    <p><b>العميل:</b> {c_name}</p>
                    <hr>
                    <p>المنتج: {p_obj.name} | الكمية: {qty}</p>
                    <h4>إجمالي الفاتورة: {total_val} $</h4>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("الكمية في المخزن لا تكفي!")

# --- 👥 القسم: العملاء ---
elif choice == "👥 العملاء":
    st.title("👥 إدارة العملاء")
    with st.form("cust_form"):
        n = st.text_input("اسم العميل")
        p = st.text_input("رقم الهاتف")
        if st.form_submit_button("إضافة عميل"):
            session.add(Customer(name=n, phone=p))
            session.commit()

    clist = session.query(Customer).all()
    for c in clist:
        col1, col2, col3 = st.columns([4, 4, 2])
        col1.write(c.name)
        col2.write(c.phone)
        if col3.button("حذف", key=f"c_{c.id}"):
            delete_item(Customer, c.id)

# --- 🧾 القسم: المالية ---
elif choice == "🧾 الرواتب والمالية":
    st.title("🧾 الرواتب والمصاريف الإدارية")
    with st.form("fin"):
        t = st.selectbox("النوع", ["رواتب", "إيجار", "كهرباء/إنترنت", "أخرى"])
        a = st.number_input("المبلغ", min_value=0.0)
        if st.form_submit_button("تسجيل"):
            session.add(Finance(type=t, amount=a))
            session.commit()
            st.success("تم الحفظ")

    fins = session.query(Finance).all()
    st.dataframe(pd.DataFrame([(f.id, f.type, f.amount) for f in fins], columns=["ID", "النوع", "المبلغ"]))
